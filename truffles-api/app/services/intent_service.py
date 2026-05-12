import json
import math
import os
import re
import time
from copy import deepcopy
from datetime import datetime, timezone
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
from app.services.policy_prompt_snapshot_service import (
    PolicyCoreBookingInfoInterruptVariantV1,
    resolve_policy_core_booking_info_interrupt_signature,
    resolve_policy_core_booking_info_interrupt_variant,
    render_policy_core_generated_contract_boundary_payload_template,
    render_policy_core_generated_contract_repair_template,
)

logger = get_logger("intent_service")
_SECONDARY_SEMANTIC_OWNER_REMOVED = "secondary_semantic_owner_removed"
_POLICY_CORE_BOUNDARY_SEMANTIC_NORMALIZATION_REASON_CODE = "boundary_semantic_normalization"
_NONREPAIRABLE_OWNER_SCHEMA_ERROR_PREFIXES = (
    "llm_policy_core_error:start_booking_temporal_clue_reclassification_required",
    "llm_policy_core_error:start_booking_exact_datetime_progression_required",
    "llm_policy_core_error:booking_availability_missing_service_reclassification_required",
    "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required",
    "llm_policy_core_error:missing_service_exact_datetime_info_interrupt_carryover_invalid",
    "llm_policy_core_error:active_booking_specialist_followup_reclassification_required",
    "llm_policy_core_error:active_booking_customer_name_carryover_required",
    "llm_policy_core_error:active_booking_time_fill_progression_required",
    "llm_policy_core_error:active_booking_commit_progression_required",
    "llm_policy_core_error:active_booking_manage_interrupt_reclassification_required",
    "llm_policy_core_error:booking_manage_name_fill_followup_invalid",
)
_BOOKING_MANAGE_REFERENCE_INTENTS = {
    "check_booking",
    "verify_booking",
    "confirm_booking",
    "booking_confirmation",
}
_POLICY_CORE_ADMIN_HANDOFF_SECTIONS = (
    "medical",
    "complaint",
    "reschedule",
    "cancel",
    "payment_info",
)
_POLICY_CORE_BOOKING_MANAGE_POLICY_SECTIONS = {"cancel", "reschedule"}
_POLICY_CORE_EXPLICIT_CLOCK_TIME_PATTERN = re.compile(
    r"(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d(?!\d)"
)
_POLICY_CORE_HOUR_TIME_PATTERN = re.compile(
    r"\b(?:в|к|на)\s*(?:[01]?\d|2[0-3])(?:\s*час(?:а|ов)?)?\b",
    re.IGNORECASE,
)
_POLICY_CORE_SPLIT_CLOCK_TIME_PATTERN = re.compile(
    r"\b(?:(?:в|к|на)\s*)?(?:[01]?\d|2[0-3])\s+[0-5]\d(?:\s*(?:утра|дня|вечера|ночи))?\b",
    re.IGNORECASE,
)
_POLICY_CORE_CLOCK_TIME_PREPOSITION_PATTERN = re.compile(
    r"\b(?:на|в|во|к|ко)\s+(?=(?:[01]?\d|2[0-3])[:.][0-5]\d\b)",
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
_POLICY_CORE_ACK_OR_CONFIRMATION_ONLY_PATTERN = re.compile(
    r"^\s*(?:да|ок|окей|okay|ok|хорошо|соглас(?:ен|на|ны)|подтверждаю|подтверждаем|confirm|yes)(?:[\s,.;!]+(?:да|ок|окей|okay|ok|хорошо|соглас(?:ен|на|ны)|подтверждаю|подтверждаем|confirm|yes))*\s*[.!?]*\s*$",
    re.IGNORECASE,
)
_POLICY_CORE_SERVICE_CANDIDATE_RESIDUE_STOP_TOKENS = {
    "а",
    "ага",
    "будет",
    "вечер",
    "вечером",
    "да",
    "днем",
    "днём",
    "есть",
    "если",
    "жоқ",
    "и",
    "к",
    "ко",
    "ли",
    "можно",
    "на",
    "нет",
    "ок",
    "окей",
    "после",
    "пожалуйста",
    "с",
    "со",
    "тогда",
    "утром",
    "хорошо",
}
_POLICY_CORE_SERVICE_PRESENCE_QUERY_STOP_TOKENS = {
    *_POLICY_CORE_SERVICE_CANDIDATE_RESIDUE_STOP_TOKENS,
    "вы",
    "делаете",
    "занимаетесь",
    "заниматься",
    "занимаетесь",
    "оказываете",
    "предлагаете",
    "услуга",
    "услуги",
    "услуг",
    "процедура",
    "процедуры",
}
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
        r"\b(?:сегодня|завтра|послезавтра|бүгін|буг[іи]н|bug[ui]n|ертең|ертен|erten|erteñ|бүрсігүні|бурс[іи]гун[іи]|bursiguni|утр(?:о|ом)|вечер(?:ом)?|дн[её]м|ноч(?:ь|ью)|после|до)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:понедельник(?:а|у|е)?|вторник(?:а|у|е)?|сред(?:а|у|е|ы)|четверг(?:а|у|е)?|пятниц(?:а|у|е|ы)|суббот(?:а|у|е|ы)|воскресень(?:е|я|ю))\b",
        re.IGNORECASE,
    ),
)
_POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN = re.compile(
    r"\b(?:сегодня|завтра|послезавтра|бүгін|буг[іи]н|bug[ui]n|ертең|ертен|erten|erteñ|бүрсігүні|бурс[іи]гун[іи]|bursiguni)\b",
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
_POLICY_CORE_MESSAGE_MONTH_DATE_PATTERN = re.compile(
    r"\b\d{1,2}\s+"
    r"(?:"
    r"январ[ья]|феврал[ья]|март[ае]?|апрел[ья]|ма[йя]|июн[ья]|июл[ья]|"
    r"август[ае]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья]|"
    r"january|february|march|april|may|june|july|august|september|october|november|december"
    r")\b",
    re.IGNORECASE,
)
_POLICY_CORE_EXPLICIT_CUSTOMER_NAME_INTRO_PATTERNS = (
    re.compile(r"\bменя\s+зовут\b", re.IGNORECASE),
    re.compile(r"\bмо[её]\s+имя\b", re.IGNORECASE),
    re.compile(r"\bmy\s+name\s+is\b", re.IGNORECASE),
    re.compile(r"\bi\s+am\b", re.IGNORECASE),
    re.compile(r"\bi['’]m\b", re.IGNORECASE),
    re.compile(
        r"^\s*(?:я|мен)\s+[A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә-]+(?:\s+[A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә-]+){0,2}[.!?]?\s*$",
        re.IGNORECASE,
    ),
)
_POLICY_CORE_PHONE_SURFACE_PATTERN = re.compile(
    r"(?P<phone>(?:\+\s*)?\d(?:[\s().-]*\d){6,14})(?!\d)"
)
_POLICY_CORE_CONTACT_LABEL_PATTERN = re.compile(
    r"\b(?:тел(?:ефон)?|phone|номер|контакт(?:ы)?)\b\s*:?",
    re.IGNORECASE,
)
_POLICY_CORE_CUSTOMER_NAME_PRONOUN_PATTERN = re.compile(
    r"\b(?:мой|моя|мо[её]|мою|мои|my)\b",
    re.IGNORECASE,
)
_POLICY_CORE_CUSTOMER_NAME_NON_IDENTITY_SIGNAL_KEYS = (
    "booking_request",
    "booking_keywords",
    "booking_verification_keywords",
    "booking_confirmation_keywords",
    "booking_cancel_keywords",
    "booking_reschedule_keywords",
    "contact_delay_keywords",
)
_POLICY_CORE_SERVICE_CARD_LABEL_SPLIT_PATTERN = re.compile(
    r"\s*(?:/|\\|&|\+|,|;|\bи\b|\band\b)\s*",
    re.IGNORECASE,
)
_POLICY_CORE_SERVICE_MODIFIER_CONNECTOR_PATTERN = re.compile(
    r"\b(?:с|со|with|including)\s+[A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә'’\-]+",
    re.IGNORECASE,
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
    int(os.environ.get("LLM_POLICY_CORE_GPT5_MIN_MAX_TOKENS", "480")),
    1,
)
POLICY_CORE_GPT5_COMPACT_MIN_MAX_TOKENS = max(
    int(os.environ.get("LLM_POLICY_CORE_GPT5_COMPACT_MIN_MAX_TOKENS", "320")),
    1,
)
POLICY_CORE_GPT5_SAFE_MAX_TOKENS = max(
    int(os.environ.get("LLM_POLICY_CORE_GPT5_SAFE_MAX_TOKENS", "480")),
    1,
)
POLICY_CORE_GPT5_COMPACT_SAFE_MAX_TOKENS = max(
    int(os.environ.get("LLM_POLICY_CORE_GPT5_COMPACT_SAFE_MAX_TOKENS", "320")),
    1,
)
POLICY_CORE_GPT5_BOOKING_MANAGE_SAFE_MAX_TOKENS = max(
    int(os.environ.get("LLM_POLICY_CORE_GPT5_BOOKING_MANAGE_SAFE_MAX_TOKENS", "560")),
    1,
)
POLICY_CORE_GPT5_MASTER_INTERRUPT_SAFE_MAX_TOKENS = max(
    int(os.environ.get("LLM_POLICY_CORE_GPT5_MASTER_INTERRUPT_SAFE_MAX_TOKENS", "480")),
    1,
)
POLICY_CORE_GPT5_FOCUSED_SAFE_MAX_TOKENS = max(
    int(os.environ.get("LLM_POLICY_CORE_GPT5_FOCUSED_SAFE_MAX_TOKENS", "320")),
    1,
)
POLICY_CORE_CONFIDENCE_THRESHOLD = float(
    os.environ.get("LLM_POLICY_CORE_CONFIDENCE_THRESHOLD", "0.3")
)
POLICY_CORE_COMPACT_TRIGGER_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_POLICY_CORE_COMPACT_TRIGGER_TIMEOUT_SECONDS", "1.8")),
    0.2,
)
POLICY_CORE_COMPACT_FIRST_ATTEMPT = (
    os.environ.get("LLM_POLICY_CORE_COMPACT_FIRST_ATTEMPT", "1").strip().casefold()
    not in {"0", "false", "no", "off"}
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


def _resolve_policy_core_governed_retry_timeout_seconds(
    timeout_seconds: float,
    *,
    sticky_full_prompt_retry: bool,
) -> float:
    retry_timeout = min(POLICY_CORE_RETRY_TIMEOUT_SECONDS, timeout_seconds)
    if sticky_full_prompt_retry:
        retry_timeout = min(
            max(POLICY_CORE_FALLBACK_TIMEOUT_SECONDS, POLICY_CORE_RETRY_TIMEOUT_SECONDS),
            timeout_seconds,
    )
    return retry_timeout


def _resolve_policy_core_empty_response_retry_timeout_seconds(timeout_seconds: float) -> float:
    return min(
        max(POLICY_CORE_RETRY_TIMEOUT_SECONDS, POLICY_CORE_MIN_TIMEOUT_SECONDS),
        timeout_seconds,
    )


def _resolve_policy_core_max_tokens(timeout_seconds: float) -> int:
    return _resolve_policy_core_max_tokens_with_cap(timeout_seconds, None)


def _resolve_policy_core_max_tokens_with_cap(
    timeout_seconds: float,
    max_tokens_override: int | None,
    model_name: str | None = None,
    *,
    compact_mode: bool = False,
    min_tokens_override: int | None = None,
    safe_cap_override: int | None = None,
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
            return resolved
        # GPT-5 on the booking hot path needs enough completion headroom to avoid
        # empty-response failures, but the old 560/800 floors were large enough
        # to turn routine owner turns into timeout-driven handoffs.
        min_tokens = min_tokens_override
        if min_tokens is None:
            min_tokens = (
                POLICY_CORE_GPT5_COMPACT_MIN_MAX_TOKENS
                if compact_mode
                else POLICY_CORE_GPT5_MIN_MAX_TOKENS
            )
        safe_cap = safe_cap_override
        if safe_cap is None:
            safe_cap = (
                POLICY_CORE_GPT5_COMPACT_SAFE_MAX_TOKENS
                if compact_mode
                else POLICY_CORE_GPT5_SAFE_MAX_TOKENS
            )
        return min(max(resolved, min_tokens), safe_cap)
    return resolved


def _policy_core_gpt5_token_profile_for_turn(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    compact_mode: bool,
    focused_interrupt_variant: PolicyCoreBookingInfoInterruptVariantV1 | None = None,
) -> tuple[int | None, int | None]:
    if compact_mode or not isinstance(normalized_memory_profile, Mapping):
        return None, None
    if (
        isinstance(focused_interrupt_variant, PolicyCoreBookingInfoInterruptVariantV1)
        and focused_interrupt_variant.head_intent == "master_query"
    ):
        target_tokens = min(
            POLICY_CORE_GPT5_SAFE_MAX_TOKENS,
            POLICY_CORE_GPT5_MASTER_INTERRUPT_SAFE_MAX_TOKENS,
        )
        return target_tokens, target_tokens
    semantic_contract = normalized_memory_profile.get("semantic_contract")
    if not isinstance(semantic_contract, Mapping):
        return None, None
    capability = _policy_core_payload_token(semantic_contract.get("capability"))
    if capability == "booking_manage":
        # Existing-booking lookup follow-ups carry a denser full-prompt contract
        # than start-booking turns. They need slightly more GPT-5 headroom than
        # the booking default, but should still stay under the old 800-token
        # drift path that was causing first-turn availability timeouts.
        target_tokens = max(
            POLICY_CORE_GPT5_SAFE_MAX_TOKENS,
            POLICY_CORE_GPT5_BOOKING_MANAGE_SAFE_MAX_TOKENS,
        )
        return target_tokens, target_tokens
    return None, None


def _policy_core_resolve_missing_service_grounded_fact_interrupt_variant(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> PolicyCoreBookingInfoInterruptVariantV1 | None:
    if not _policy_core_has_missing_service_exact_datetime_service_choice_context(
        normalized_memory_profile
    ):
        return None
    grounded_service = _policy_core_resolve_current_message_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    if not grounded_service:
        return None
    service_multifact_refs = _policy_core_current_message_service_multifact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if service_multifact_refs == ["pricing", "duration"]:
        return resolve_policy_core_booking_info_interrupt_variant(
            intent="pricing",
            capability="pricing",
            pack_refs=("pricing", "duration"),
            family="service_grounding_progression",
        )
    if _policy_core_current_message_has_promotions_query(current_message):
        return resolve_policy_core_booking_info_interrupt_variant(
            intent="promotions",
            capability="promotions",
            pack_refs=("promotions",),
            family="service_grounding_progression",
        )
    normalized_message = _normalize_text(current_message)
    if normalized_message:
        from app.services.pack_runtime_service import get_pack_runtime

        try:
            pack_runtime = get_pack_runtime(client_slug)
        except Exception:
            pack_runtime = None
        if pack_runtime is not None:
            try:
                if pack_runtime.has_duration_signal(
                    normalized_message,
                    message=current_message,
                ):
                    return resolve_policy_core_booking_info_interrupt_variant(
                        intent="duration",
                        capability="duration",
                        pack_refs=("duration",),
                        family="service_grounding_progression",
                    )
            except Exception:
                pass
            try:
                if pack_runtime.has_price_signal(
                    normalized_message,
                    message=current_message,
                ):
                    return resolve_policy_core_booking_info_interrupt_variant(
                        intent="pricing",
                        capability="pricing",
                        pack_refs=("pricing",),
                        family="service_grounding_progression",
                    )
            except Exception:
                pass
    if _policy_core_current_message_has_master_query_signal(
        current_message,
        client_slug=client_slug,
    ):
        return resolve_policy_core_booking_info_interrupt_variant(
            intent="master_query",
            capability="master",
            pack_refs=("master",),
            family="service_grounding_progression",
        )
    return None


def _policy_core_narrow_missing_service_grounded_fact_interrupt_owner_envelope(
    allowed_payload: Mapping[str, Any],
    context_payload: Mapping[str, Any] | None,
    *,
    variant: PolicyCoreBookingInfoInterruptVariantV1,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    narrowed_allowed = dict(allowed_payload)
    narrowed_allowed["info_refs"] = list(variant.pack_refs)
    narrowed_allowed["consult_refs"] = []
    raw_tool_actions = [
        action
        for action in list(narrowed_allowed.get("tool_actions") or [])
        if isinstance(action, str) and action.strip()
    ]
    desired_tool_actions = (variant.tool_action_hint, "collect", "handoff")
    narrowed_tool_actions = [action for action in desired_tool_actions if action in raw_tool_actions]
    if variant.tool_action_hint in raw_tool_actions:
        narrowed_allowed["tool_actions"] = narrowed_tool_actions
    narrowed_context = dict(context_payload) if isinstance(context_payload, Mapping) else {}
    narrowed_context.pop("consult_cards", None)
    return narrowed_allowed, narrowed_context or None


def _policy_core_missing_service_grounded_fact_interrupt_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    variant: PolicyCoreBookingInfoInterruptVariantV1 | None,
    grounded_service: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(variant, PolicyCoreBookingInfoInterruptVariantV1):
        return None
    carried_alternate_datetime = _policy_core_memory_alternate_datetime(
        normalized_memory_profile
    )
    if not carried_alternate_datetime:
        return None
    forced_fields: dict[str, Any] = {
        "intent": variant.head_intent,
        "action": "fact",
        "tool_action_hint": variant.tool_action_hint,
        "pack_refs": list(variant.pack_refs),
        "expected_reply_type": "name",
        "next_question": "name",
        "open_questions": ["name"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "service",
        "capability": variant.capability,
        "temporal_scope": "specific_time",
        "alternate_datetime": carried_alternate_datetime,
        "resolution_mode": "policy_fact",
        "pending_question_act": "fill_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "generic_info_interrupt",
    }
    if isinstance(grounded_service, str) and grounded_service.strip():
        service_value = " ".join(grounded_service.split())
        forced_fields["slots"] = {
            "service": service_value,
            "datetime": carried_alternate_datetime,
        }
        forced_fields["referents"] = {
            "service": {
                "value": service_value,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "message_grounding",
            }
        }
    return forced_fields


def _policy_core_start_booking_exact_datetime_collect_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(normalized_memory_profile) or _policy_core_active_pending_contract(
        normalized_memory_profile
    ):
        return None
    if not _policy_core_current_message_has_booking_desire_signal(
        current_message,
        client_slug=client_slug,
    ):
        return None
    if not isinstance(grounded_service, str) or not grounded_service.strip():
        return None
    exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    if not exact_datetime:
        return None
    service_value = " ".join(grounded_service.split())
    customer_phone = _policy_core_current_message_customer_phone_surface(
        current_message
    )
    customer_name = (
        _policy_core_current_message_customer_name_surface(current_message)
        or (
            _policy_core_current_message_inline_customer_name_surface(
                current_message=current_message,
                service_value=service_value,
                exact_datetime=exact_datetime,
                client_slug=client_slug,
            )
            if customer_phone
            else None
        )
    )
    if customer_name:
        if not customer_phone:
            return _policy_core_collect_phone_forced_fields(
                service_value=service_value,
                datetime_value=exact_datetime,
                customer_name=customer_name,
                service_source_ref="message_grounding",
                customer_source_ref="message_grounding",
                reason="start_booking_exact_datetime_collect_contact_phone",
            )
        return _policy_core_book_slot_forced_fields(
            service_value=service_value,
            datetime_value=exact_datetime,
            customer_name=customer_name,
            customer_phone=customer_phone,
            source_ref="message_grounding",
            reason="start_booking_exact_datetime_direct_book_slot",
        )
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "expected_reply_type": "name",
        "next_question": "name",
        "open_questions": ["name"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": "specific_time",
        "alternate_datetime": exact_datetime,
        "resolution_mode": "direct",
        "slots": {
            "service": service_value,
            "datetime": exact_datetime,
        },
        "referents": {
            "service": {
                "value": service_value,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "message_grounding",
            }
        },
        "pending_question_act": "fill_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "fill_requested_slot",
    }


def _policy_core_start_booking_exact_datetime_missing_service_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(normalized_memory_profile) or _policy_core_active_pending_contract(
        normalized_memory_profile
    ):
        return None
    if not _policy_core_current_message_has_booking_desire_signal(
        current_message,
        client_slug=client_slug,
    ):
        return None
    if isinstance(grounded_service, str) and grounded_service.strip():
        return None
    exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    if not exact_datetime:
        return None
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "slots": {"datetime": exact_datetime},
        "expected_reply_type": "service_choice",
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "general",
        "capability": "bookability",
        "temporal_scope": "specific_time",
        "alternate_datetime": exact_datetime,
        "resolution_mode": "clarify_missing_subject",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
    }


def _policy_core_start_booking_service_collect_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(normalized_memory_profile) or _policy_core_active_pending_contract(
        normalized_memory_profile
    ):
        return None
    if not _policy_core_current_message_has_booking_side_ask(current_message):
        return None
    if _policy_core_current_message_exact_datetime_surface(current_message):
        return None
    if _policy_core_current_message_has_day_or_date_clue(current_message):
        return None
    if (
        _policy_core_current_message_has_service_presence_query(current_message)
        or _policy_core_current_message_has_location_side_ask(current_message)
        or _policy_core_current_message_has_hours_ask(current_message)
        or _policy_core_current_message_has_promotions_query(current_message)
        or _policy_core_current_message_is_hypothetical_cancel_query(current_message)
    ):
        return None
    service_value = (
        " ".join(grounded_service.split())
        if isinstance(grounded_service, str) and grounded_service.strip()
        else None
    )
    if not service_value:
        return None
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "slots": {"service": service_value},
        "expected_reply_type": "time",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "goal": "booking",
        "referents": {
            "service": {
                "value": service_value,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "message_grounding",
            }
        },
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "direct",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
    }


def _policy_core_service_referent(
    service_value: str,
    *,
    source_ref: str,
) -> dict[str, Any]:
    return {
        "value": service_value,
        "entity_id": None,
        "entity_type": "service",
        "source_ref": source_ref,
    }


def _policy_core_collect_name_forced_fields(
    *,
    service_value: str,
    datetime_value: str,
    temporal_scope: str = "specific_time",
    source_ref: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "expected_reply_type": "name",
        "next_question": "name",
        "open_questions": ["name"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": temporal_scope,
        "alternate_datetime": datetime_value,
        "resolution_mode": "direct",
        "slots": {
            "service": service_value,
            "datetime": datetime_value,
        },
        "referents": {
            "service": _policy_core_service_referent(
                service_value,
                source_ref=source_ref,
            )
        },
        "pending_question_act": "fill_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "fill_requested_slot",
        "reason": reason,
    }


def _policy_core_collect_phone_forced_fields(
    *,
    service_value: str,
    datetime_value: str,
    customer_name: str,
    temporal_scope: str = "specific_time",
    service_source_ref: str,
    customer_source_ref: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "expected_reply_type": "phone",
        "next_question": "phone",
        "open_questions": ["phone"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": temporal_scope,
        "alternate_datetime": datetime_value,
        "resolution_mode": "direct",
        "slots": {
            "service": service_value,
            "datetime": datetime_value,
            "name": customer_name,
        },
        "referents": {
            "service": _policy_core_service_referent(
                service_value,
                source_ref=service_source_ref,
            ),
            "customer": {
                "value": customer_name,
                "entity_id": None,
                "entity_type": "customer",
                "source_ref": customer_source_ref,
            },
        },
        "pending_question_act": "fill_requested_slot",
        "pending_question_target": "phone",
        "active_question_relation": "fill_requested_slot",
        "reason": reason,
    }


def _policy_core_book_slot_forced_fields(
    *,
    service_value: str,
    datetime_value: str,
    customer_name: str,
    customer_phone: str | None,
    source_ref: str,
    reason: str,
) -> dict[str, Any]:
    slots: dict[str, Any] = {
        "service": service_value,
        "datetime": datetime_value,
        "name": customer_name,
    }
    if isinstance(customer_phone, str) and customer_phone.strip():
        slots["phone"] = customer_phone.strip()
    return {
        "intent": "booking",
        "action": "fact",
        "tool_action_hint": "calendar.book_slot",
        "pack_refs": [],
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": "specific_time",
        "alternate_datetime": datetime_value,
        "resolution_mode": "live_calendar",
        "slots": slots,
        "referents": {
            "service": _policy_core_service_referent(
                service_value,
                source_ref=source_ref,
            )
        },
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "reason": reason,
    }


def _policy_core_message_has_pack_signal(
    current_message: str | None,
    *,
    client_slug: str | None,
    key: str,
) -> bool:
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return False
    try:
        from app.services.pack_runtime_service import get_signal_lexicon_list

        signals = get_signal_lexicon_list(client_slug, key)
    except Exception:
        signals = []
    for signal in signals:
        normalized_signal = _normalize_text(signal)
        if normalized_signal and normalized_signal in normalized_message:
            return True
    return False


def _policy_core_current_message_has_booking_desire_signal(
    current_message: str | None,
    *,
    client_slug: str | None,
) -> bool:
    if _policy_core_current_message_has_temporal_booking_side_ask(current_message):
        return True
    return bool(
        _policy_core_message_has_pack_signal(
            current_message,
            client_slug=client_slug,
            key="booking_desire_keywords",
        )
        or _policy_core_message_has_pack_signal(
            current_message,
            client_slug=client_slug,
            key="booking_request",
        )
    )


def _policy_core_current_message_has_service_modifier_connector(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    return bool(
        normalized
        and _POLICY_CORE_SERVICE_MODIFIER_CONNECTOR_PATTERN.search(normalized)
    )


def _policy_core_memory_customer_name(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> str | None:
    slot_name = _policy_core_memory_slot_value(normalized_memory_profile, "name")
    if slot_name:
        return " ".join(slot_name.split())
    if not isinstance(normalized_memory_profile, Mapping):
        return None
    semantic_contract = normalized_memory_profile.get("semantic_contract")
    if not isinstance(semantic_contract, Mapping):
        return None
    raw_slots = semantic_contract.get("slots")
    if isinstance(raw_slots, Mapping):
        raw_name = raw_slots.get("name") or raw_slots.get("customer_name")
        if isinstance(raw_name, str) and raw_name.strip():
            return " ".join(raw_name.split())
    raw_referents = semantic_contract.get("referents")
    raw_customer = (
        raw_referents.get("customer") if isinstance(raw_referents, Mapping) else None
    )
    if isinstance(raw_customer, Mapping):
        raw_value = raw_customer.get("value")
        if isinstance(raw_value, str) and raw_value.strip():
            return " ".join(raw_value.split())
    return None


def _policy_core_memory_customer_phone(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> str | None:
    slot_phone = _policy_core_memory_slot_value(normalized_memory_profile, "phone")
    if slot_phone:
        return " ".join(slot_phone.split())
    if not isinstance(normalized_memory_profile, Mapping):
        return None
    semantic_contract = normalized_memory_profile.get("semantic_contract")
    if not isinstance(semantic_contract, Mapping):
        return None
    raw_slots = semantic_contract.get("slots")
    if isinstance(raw_slots, Mapping):
        raw_phone = raw_slots.get("phone") or raw_slots.get("contact")
        if isinstance(raw_phone, str) and raw_phone.strip():
            return " ".join(raw_phone.split())
    return None


def _policy_core_memory_active_goal(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(normalized_memory_profile, Mapping):
        return None
    return _policy_core_payload_token(normalized_memory_profile.get("active_goal"))


def _policy_core_memory_semantic_contract(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if not isinstance(normalized_memory_profile, Mapping):
        return {}
    semantic_contract = normalized_memory_profile.get("semantic_contract")
    return semantic_contract if isinstance(semantic_contract, Mapping) else {}


def _policy_core_memory_has_handoff_context(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    active_goal = _policy_core_memory_active_goal(normalized_memory_profile)
    if active_goal in {"handoff", "consult"}:
        return True
    semantic_contract = _policy_core_memory_semantic_contract(normalized_memory_profile)
    requested_effect = _policy_core_payload_token(semantic_contract.get("requested_effect"))
    tool_action_hint = _policy_core_payload_token(semantic_contract.get("tool_action_hint"))
    needs_human = semantic_contract.get("needs_human")
    return bool(
        requested_effect == "handoff_to_human"
        or tool_action_hint == "handoff"
        or needs_human is True
    )


def _policy_core_handoff_customer_payload(
    *,
    customer_name: str | None,
    customer_phone: str | None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    slots: dict[str, Any] = {}
    referents: dict[str, dict[str, Any]] = {}
    if customer_name:
        slots["name"] = customer_name
        referents["customer"] = {
            "value": customer_name,
            "entity_id": None,
            "entity_type": "customer",
            "source_ref": "message_grounding",
        }
    if customer_phone:
        slots["phone"] = customer_phone
    return slots, referents


def _policy_core_handoff_forced_fields(
    *,
    intent: str,
    reason: str,
    subject_kind: str,
    capability: str,
    risk_signals: list[str] | None = None,
    slots: dict[str, Any] | None = None,
    referents: dict[str, dict[str, Any]] | None = None,
    goal: str = "handoff",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "intent": intent,
        "action": "handoff",
        "tool_action_hint": "handoff",
        "pack_refs": [],
        "slots": dict(slots or {}),
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": True,
        "goal": goal,
        "subject_kind": subject_kind,
        "capability": capability,
        "temporal_scope": "none",
        "resolution_mode": "direct",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "risk_signals": list(risk_signals or []),
        "reason": reason,
    }
    if referents:
        payload["referents"] = dict(referents)
    return payload


def _policy_core_handoff_context_contact_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile):
        return None
    if not _policy_core_memory_has_handoff_context(normalized_memory_profile):
        return None
    customer_name = _policy_core_current_message_customer_name_surface(current_message)
    customer_phone = _policy_core_current_message_customer_phone_surface(current_message)
    if not customer_phone:
        return None
    if _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
        return None
    semantic_contract = _policy_core_memory_semantic_contract(normalized_memory_profile)
    subject_kind = _policy_core_payload_token(semantic_contract.get("subject_kind")) or "general"
    capability = _policy_core_payload_token(semantic_contract.get("capability")) or "other"
    slots, referents = _policy_core_handoff_customer_payload(
        customer_name=customer_name,
        customer_phone=customer_phone,
    )
    carried_referents = semantic_contract.get("referents")
    if isinstance(carried_referents, Mapping):
        for key in ("service", "specialist", "branch", "booking_ref"):
            payload = carried_referents.get(key)
            if isinstance(payload, Mapping) and payload:
                referents.setdefault(key, dict(payload))
    return _policy_core_handoff_forced_fields(
        intent="handoff_context_update",
        reason="handoff_context_contact_update",
        subject_kind=subject_kind,
        capability=capability,
        risk_signals=["handoff_context"],
        slots=slots,
        referents=referents,
    )


def _policy_core_booking_manage_handoff_context_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
) -> dict[str, Any] | None:
    if not isinstance(normalized_memory_profile, Mapping):
        return None
    if _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile):
        return None
    if not _policy_core_memory_has_handoff_context(normalized_memory_profile):
        return None
    semantic_contract = _policy_core_memory_semantic_contract(normalized_memory_profile)
    if _policy_core_payload_token(semantic_contract.get("capability")) != "booking_manage":
        return None

    customer_name = _policy_core_current_message_customer_name_surface(current_message)
    customer_phone = _policy_core_current_message_customer_phone_surface(current_message)
    temporal_surface = _policy_core_current_message_temporal_context_surface(current_message)
    service_value = (
        " ".join(grounded_service.split())
        if isinstance(grounded_service, str) and grounded_service.strip()
        else None
    )
    if not any((customer_name, customer_phone, temporal_surface, service_value)):
        return None

    slots, referents = _policy_core_handoff_customer_payload(
        customer_name=customer_name,
        customer_phone=customer_phone,
    )
    if service_value:
        slots["service"] = service_value
        referents["service"] = _policy_core_service_referent(
            service_value,
            source_ref="message_grounding",
        )
    if temporal_surface:
        slots["datetime"] = temporal_surface

    carried_referents = semantic_contract.get("referents")
    if isinstance(carried_referents, Mapping):
        for key in ("service", "specialist", "branch", "booking_ref", "customer"):
            payload = carried_referents.get(key)
            if isinstance(payload, Mapping) and payload:
                referents.setdefault(key, dict(payload))

    forced_fields = _policy_core_handoff_forced_fields(
        intent="handoff_context_update",
        reason="booking_manage_handoff_context_update",
        subject_kind=_policy_core_payload_token(semantic_contract.get("subject_kind")) or "booking",
        capability="booking_manage",
        risk_signals=["handoff_context", "booking_manage"],
        slots=slots,
        referents=referents,
    )
    temporal_scope = _policy_core_current_message_grounded_temporal_scope_hint(
        current_message,
    )
    if temporal_surface:
        forced_fields["alternate_datetime"] = temporal_surface
    if temporal_scope:
        forced_fields["temporal_scope"] = temporal_scope
    return forced_fields


def _policy_core_identity_first_booking_collect_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile):
        return None
    if _policy_core_memory_has_handoff_context(normalized_memory_profile):
        return None
    if _policy_core_memory_unsupported_service_fact(normalized_memory_profile):
        return None
    customer_name = _policy_core_current_message_customer_name_surface(current_message)
    customer_phone = _policy_core_current_message_customer_phone_surface(current_message)
    if not customer_name or not customer_phone:
        return None
    if _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
        return None
    slots = {"name": customer_name, "phone": customer_phone}
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "slots": slots,
        "referents": {
            "customer": {
                "value": customer_name,
                "entity_id": None,
                "entity_type": "customer",
                "source_ref": "message_grounding",
            }
        },
        "expected_reply_type": "service_choice",
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "clarify_missing_subject",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "reason": "customer_identity_provided_before_booking_details",
    }


def _policy_core_active_booking_contact_carryover_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return None
    if _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
        return None

    customer_name = _policy_core_current_message_customer_name_surface(current_message)
    customer_phone = _policy_core_current_message_customer_phone_surface(current_message)
    if not customer_name and not customer_phone:
        return None

    grounded_service = _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return None

    carried_name = customer_name or _policy_core_memory_slot_value(
        normalized_memory_profile,
        "name",
    )
    carried_phone = customer_phone or _policy_core_memory_slot_value(
        normalized_memory_profile,
        "phone",
    )
    carried_alternate_datetime = _policy_core_memory_alternate_datetime(
        normalized_memory_profile
    )
    carried_temporal_scope = (
        _policy_core_memory_temporal_scope(normalized_memory_profile) or "none"
    )
    carried_datetime = carried_alternate_datetime or _policy_core_memory_slot_value(
        normalized_memory_profile,
        "datetime",
    )

    slots: dict[str, Any] = {"service": grounded_service}
    if carried_datetime:
        slots["datetime"] = carried_datetime
    if carried_name:
        slots["name"] = carried_name
    if carried_phone:
        slots["phone"] = carried_phone

    semantic_contract = _policy_core_memory_semantic_contract(normalized_memory_profile)
    referents: dict[str, Any] = {}
    raw_referents = semantic_contract.get("referents")
    if isinstance(raw_referents, Mapping):
        for key in ("service", "specialist", "branch", "booking_ref"):
            payload = raw_referents.get(key)
            if isinstance(payload, Mapping) and payload:
                referents[key] = dict(payload)
    referents.setdefault(
        "service",
        {
            "value": grounded_service,
            "entity_id": None,
            "entity_type": "service",
            "source_ref": "memory.semantic_contract",
        },
    )
    if carried_name:
        referents["customer"] = {
            "value": carried_name,
            "entity_id": None,
            "entity_type": "customer",
            "source_ref": "message_grounding" if customer_name else "memory.slot_state",
        }

    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "slots": slots,
        "referents": referents,
        "expected_reply_type": carry_contract.get("expected_reply_type") or "time",
        "next_question": carry_contract.get("next_question") or "datetime",
        "open_questions": _policy_core_expected_open_questions(carry_contract) or ["datetime"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": carried_temporal_scope,
        "alternate_datetime": carried_alternate_datetime,
        "resolution_mode": "direct",
        "pending_question_act": carry_contract.get("pending_question_act"),
        "pending_question_target": carry_contract.get("pending_question_target") or "time",
        "active_question_relation": carry_contract.get("active_question_relation"),
        "reason": "active_booking_contact_carryover_while_time_pending",
    }


def _policy_core_current_message_booking_manage_signal(
    current_message: str | None,
    *,
    client_slug: str | None,
) -> str | None:
    if _policy_core_message_has_pack_signal(
        current_message,
        client_slug=client_slug,
        key="booking_reschedule_keywords",
    ):
        return "reschedule"
    if _policy_core_message_has_pack_signal(
        current_message,
        client_slug=client_slug,
        key="booking_cancel_keywords",
    ):
        return "cancel"
    return None


def _policy_core_standalone_booking_manage_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile):
        return None
    manage_signal = _policy_core_current_message_booking_manage_signal(
        current_message,
        client_slug=client_slug,
    )
    if manage_signal is None:
        return None

    name = _policy_core_current_message_customer_name_surface(current_message)
    phone = _policy_core_current_message_customer_phone_surface(current_message)
    exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    temporal_scope = (
        _policy_core_current_message_grounded_temporal_scope_hint(current_message)
        or "none"
    )
    slots: dict[str, Any] = {}
    referents: dict[str, dict[str, Any]] = {}
    if name:
        slots["name"] = name
        referents["customer"] = {
            "value": name,
            "entity_id": None,
            "entity_type": "customer",
            "source_ref": "message_grounding",
        }
    if phone:
        slots["phone"] = phone
    if exact_datetime:
        slots["datetime"] = exact_datetime

    has_customer = bool(name)
    has_lookup_datetime = bool(exact_datetime)
    direct_lookup = has_customer and has_lookup_datetime
    next_question = None if direct_lookup else ("datetime" if has_customer else "name")
    expected_reply_type = None if direct_lookup else ("time" if has_customer else "name")
    open_questions = [] if direct_lookup else [next_question]
    forced_fields: dict[str, Any] = {
        "intent": "check_booking",
        "action": "fact",
        "tool_action_hint": "calendar.get_booking",
        "pack_refs": [],
        "slots": slots,
        "expected_reply_type": expected_reply_type,
        "next_question": next_question,
        "open_questions": open_questions,
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "booking_manage",
        "temporal_scope": temporal_scope,
        "resolution_mode": "direct",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "reason": f"user_requests_{manage_signal}_existing_booking_without_booking_ref",
    }
    if exact_datetime:
        forced_fields["alternate_datetime"] = exact_datetime
    if referents:
        forced_fields["referents"] = referents
    return forced_fields


def _policy_core_booking_manage_reference_slot_carryover_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
) -> dict[str, Any] | None:
    semantic_contract = _policy_core_memory_semantic_contract(normalized_memory_profile)
    if _policy_core_payload_token(semantic_contract.get("capability")) != "booking_manage":
        return None
    if _policy_core_payload_token(semantic_contract.get("subject_kind")) != "booking":
        return None
    referents = semantic_contract.get("referents")
    if _policy_core_has_grounded_referent(
        referents if isinstance(referents, Mapping) else None,
        "booking_ref",
    ):
        return None

    current_name = _policy_core_current_message_customer_name_surface(current_message)
    current_phone = _policy_core_current_message_customer_phone_surface(current_message)
    service_value = (
        " ".join(grounded_service.split())
        if isinstance(grounded_service, str) and grounded_service.strip()
        else (
            _policy_core_memory_slot_value(normalized_memory_profile, "service")
            or _policy_core_memory_grounded_service(normalized_memory_profile)
        )
    )
    service_value = " ".join(service_value.split()) if isinstance(service_value, str) else None
    current_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    if not current_datetime and _policy_core_current_message_has_message_grounded_temporal_clue(
        current_message
    ):
        current_datetime = (
            _policy_core_current_message_temporal_context_surface(current_message)
            or _policy_core_normalize_surface_text(current_message)
        )
        if current_datetime and service_value:
            current_datetime = re.sub(
                rf"(?<!\w){re.escape(service_value)}(?!\w)",
                " ",
                current_datetime,
                flags=re.IGNORECASE,
            )
            current_datetime = " ".join(current_datetime.split()).strip(" ,.!?:;")

    memory_datetime = (
        _policy_core_memory_alternate_datetime(normalized_memory_profile)
        or _policy_core_memory_slot_value(normalized_memory_profile, "datetime")
    )
    datetime_value = current_datetime or memory_datetime
    customer_name = current_name or _policy_core_memory_customer_name(normalized_memory_profile)
    customer_phone = current_phone or _policy_core_memory_customer_phone(normalized_memory_profile)
    has_current_signal = any(
        value
        for value in (
            current_name,
            current_phone,
            current_datetime,
            grounded_service,
        )
    )
    has_lookup_context = bool((customer_name or customer_phone) and datetime_value)
    if not has_current_signal and not (
        has_lookup_context and _policy_core_current_message_is_ack_or_confirmation(current_message)
    ):
        return None

    slots: dict[str, Any] = {}
    if service_value:
        slots["service"] = service_value
    if datetime_value:
        slots["datetime"] = datetime_value
    if customer_name:
        slots["name"] = customer_name
    if customer_phone:
        slots["phone"] = customer_phone

    referent_payload: dict[str, dict[str, Any]] = {}
    if service_value:
        referent_payload["service"] = {
            "value": service_value,
            "entity_id": None,
            "entity_type": "service",
            "source_ref": "message_grounding" if grounded_service else "memory.semantic_contract",
        }
    if customer_name:
        referent_payload["customer"] = {
            "value": customer_name,
            "entity_id": None,
            "entity_type": "customer",
            "source_ref": "message_grounding" if current_name else "memory.slot_state",
        }

    if has_lookup_context and _policy_core_current_message_is_ack_or_confirmation(current_message):
        return _policy_core_handoff_forced_fields(
            intent="check_booking",
            reason="booking_manage_confirmation_without_matching_record_requires_admin",
            subject_kind="booking",
            capability="booking_manage",
            risk_signals=["booking_manage", "booking_lookup_not_found"],
            slots=slots,
            referents=referent_payload,
            goal="booking",
        )

    expected_reply_type = None if has_lookup_context else ("time" if customer_name or customer_phone else "name")
    next_question = None if has_lookup_context else ("datetime" if customer_name or customer_phone else "name")
    open_questions = [] if next_question is None else [next_question]
    temporal_scope = (
        _policy_core_current_message_grounded_temporal_scope_hint(current_message)
        or _policy_core_memory_temporal_scope(normalized_memory_profile)
        or ("day" if _policy_core_day_date_surface(datetime_value) else "none")
    )
    return {
        "intent": "check_booking",
        "action": "fact",
        "tool_action_hint": "calendar.get_booking",
        "pack_refs": [],
        "slots": slots,
        "expected_reply_type": expected_reply_type,
        "next_question": next_question,
        "open_questions": open_questions,
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "booking_manage",
        "temporal_scope": temporal_scope,
        "alternate_datetime": datetime_value,
        "resolution_mode": "direct",
        "referents": referent_payload,
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "reason": "calendar_get_booking_reference_slot_carryover",
    }


def _policy_core_policy_section(
    client_slug: str | None,
    section_key: str,
) -> Mapping[str, Any] | None:
    try:
        from app.services.pack_runtime_service import get_pack_runtime

        truth = get_pack_runtime(client_slug).load_yaml_truth()
    except Exception:
        truth = {}
    policy = truth.get("policy") if isinstance(truth, Mapping) else None
    section = policy.get(section_key) if isinstance(policy, Mapping) else None
    return section if isinstance(section, Mapping) else None


def _policy_core_message_matches_policy_section(
    current_message: str | None,
    *,
    client_slug: str | None,
    section_key: str,
) -> bool:
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return False
    section = _policy_core_policy_section(client_slug, section_key)
    keywords = section.get("keywords") if isinstance(section, Mapping) else None
    if not isinstance(keywords, list):
        return False
    for keyword in keywords:
        normalized_keyword = _normalize_text(keyword)
        if normalized_keyword and normalized_keyword in normalized_message:
            return True
    return False


def _policy_core_policy_handoff_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    client_slug: str | None,
    grounded_service: str | None,
) -> dict[str, Any] | None:
    matched_section_key: str | None = None
    for section_key in _POLICY_CORE_ADMIN_HANDOFF_SECTIONS:
        if _policy_core_message_matches_policy_section(
            current_message,
            client_slug=client_slug,
            section_key=section_key,
        ):
            matched_section_key = section_key
            break
    explicit_human_request = is_human_request_message(current_message or "")
    if matched_section_key is None and not explicit_human_request:
        return None

    service_value = (
        " ".join(grounded_service.split())
        if isinstance(grounded_service, str) and grounded_service.strip()
        else None
    )
    current_message_customer_name = (
        _policy_core_current_message_customer_name_surface(current_message)
        if _policy_core_current_message_has_explicit_customer_name_intro(current_message)
        else None
    )
    slots, referents = _policy_core_handoff_customer_payload(
        customer_name=current_message_customer_name,
        customer_phone=_policy_core_current_message_customer_phone_surface(current_message),
    )
    memory_customer_name = _policy_core_memory_customer_name(normalized_memory_profile)
    memory_customer_phone = _policy_core_memory_customer_phone(normalized_memory_profile)
    if memory_customer_name and "name" not in slots:
        slots["name"] = memory_customer_name
        referents.setdefault(
            "customer",
            {
                "value": memory_customer_name,
                "entity_id": None,
                "entity_type": "customer",
                "source_ref": "memory.semantic_contract",
            },
        )
    if memory_customer_phone and "phone" not in slots:
        slots["phone"] = memory_customer_phone
    if service_value:
        slots["service"] = service_value
        referents["service"] = {
            "value": service_value,
            "entity_id": None,
            "entity_type": "service",
            "source_ref": "message_grounding",
        }

    semantic_contract = _policy_core_memory_semantic_contract(normalized_memory_profile)
    carried_referents = semantic_contract.get("referents")
    if isinstance(carried_referents, Mapping):
        for key in ("service", "specialist", "branch", "booking_ref", "customer"):
            payload = carried_referents.get(key)
            if isinstance(payload, Mapping) and payload:
                referents.setdefault(key, dict(payload))
    active_capability = _policy_core_payload_token(semantic_contract.get("capability"))
    section_intent = matched_section_key
    if matched_section_key is not None:
        section = _policy_core_policy_section(client_slug, matched_section_key)
        section_intent = (
            _policy_core_payload_token(section.get("intent"))
            if isinstance(section, Mapping)
            else None
        ) or matched_section_key

    booking_manage_context = bool(
        matched_section_key in _POLICY_CORE_BOOKING_MANAGE_POLICY_SECTIONS
        or active_capability == "booking_manage"
    )
    subject_kind = "booking" if booking_manage_context else ("service" if service_value else "general")
    capability = "booking_manage" if booking_manage_context else (
        "consultation" if matched_section_key == "medical" else "other"
    )
    reason_key = matched_section_key or "human_request"
    return _policy_core_handoff_forced_fields(
        intent=section_intent or "handoff",
        reason=f"policy_{reason_key}_requires_admin_handoff",
        subject_kind=subject_kind,
        capability=capability,
        risk_signals=[reason_key],
        slots=slots,
        referents=referents,
    )


def _policy_core_remove_pack_signals(
    value: str,
    *,
    client_slug: str | None,
    keys: Iterable[str],
) -> str:
    cleaned = value
    try:
        from app.services.pack_runtime_service import get_signal_lexicon_list
    except Exception:
        get_signal_lexicon_list = None
    normalized_signals: list[str] = []
    for key in keys:
        signals = (
            get_signal_lexicon_list(client_slug, key)
            if get_signal_lexicon_list is not None
            else []
        )
        for signal in signals:
            normalized_signal = _normalize_text(signal)
            if normalized_signal:
                normalized_signals.append(normalized_signal)
    phrase_signals = {
        signal.casefold()
        for signal in normalized_signals
        if any(character.isspace() for character in signal)
    }
    token_signals = {
        signal.casefold()
        for signal in normalized_signals
        if not any(character.isspace() for character in signal)
    }
    for signal in sorted(phrase_signals, key=len, reverse=True):
        cleaned = re.sub(
            rf"(?<!\w){re.escape(signal)}(?!\w)",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
    cleaned_tokens: list[str] = []
    for token in cleaned.split():
        normalized_token = token.casefold()
        remove_token = False
        for signal in token_signals:
            if normalized_token == signal or (
                len(signal) >= 4 and normalized_token.startswith(signal)
            ):
                remove_token = True
                break
        if not remove_token:
            cleaned_tokens.append(token)
    cleaned = " ".join(cleaned_tokens)
    return " ".join(cleaned.split())


def _policy_core_service_candidate_from_residue(
    value: str | None,
    *,
    stop_tokens: set[str],
) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None
    cleaned = re.sub(r"[^0-9A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә'’\-\s]", " ", normalized)
    candidate_tokens = [
        token
        for token in cleaned.split()
        if token.casefold() not in stop_tokens and not token.isdigit()
    ]
    candidate = " ".join(candidate_tokens).strip()
    if not candidate or len(candidate) > 80:
        return None
    return candidate


def _policy_core_unsupported_service_availability_candidate(
    current_message: str | None,
    *,
    grounded_service: str | None,
) -> str | None:
    if isinstance(grounded_service, str) and grounded_service.strip():
        return None
    if not _policy_core_current_message_has_service_presence_query(current_message):
        return None
    cleaned = _normalize_text(current_message)
    if not cleaned:
        return None
    for pattern in _POLICY_CORE_SERVICE_PRESENCE_QUERY_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    return _policy_core_service_candidate_from_residue(
        cleaned,
        stop_tokens=_POLICY_CORE_SERVICE_PRESENCE_QUERY_STOP_TOKENS,
    )


def _policy_core_unsupported_service_availability_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(
        normalized_memory_profile
    ) or _policy_core_resume_pending_contract(normalized_memory_profile):
        return None
    service_candidate = _policy_core_unsupported_service_availability_candidate(
        current_message,
        grounded_service=grounded_service,
    )
    if not service_candidate:
        return None
    return {
        "intent": "out_of_domain",
        "action": "fact",
        "tool_action_hint": "catalog.service_query",
        "pack_refs": ["services_overview"],
        "slots": {"service": service_candidate},
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "goal": None,
        "referents": {
            "service": {
                "value": service_candidate,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "surface",
            }
        },
        "subject_kind": "service",
        "capability": "other",
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "reason": "unsupported_service_availability_fact",
    }


def _policy_core_unsupported_service_booking_continuation_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(
        normalized_memory_profile
    ) or _policy_core_resume_pending_contract(normalized_memory_profile):
        return None
    unsupported_service = _policy_core_memory_unsupported_service_fact(
        normalized_memory_profile
    )
    if not unsupported_service:
        return None
    if isinstance(grounded_service, str) and grounded_service.strip():
        return None
    customer_name = _policy_core_current_message_customer_name_surface(current_message)
    customer_phone = _policy_core_current_message_customer_phone_surface(current_message)
    has_identity_context = bool(customer_name or customer_phone)
    has_booking_continuation_signal = _policy_core_current_message_has_booking_desire_signal(
        current_message,
        client_slug=client_slug,
    )
    if not (has_booking_continuation_signal or has_identity_context):
        return None
    if not (
        _policy_core_current_message_has_message_grounded_temporal_clue(current_message)
        or _policy_core_current_message_has_temporal_booking_side_ask(current_message)
        or has_identity_context
    ):
        return None
    if customer_phone:
        slots, referents = _policy_core_handoff_customer_payload(
            customer_name=customer_name,
            customer_phone=customer_phone,
        )
        slots["service"] = unsupported_service
        referents["service"] = {
            "value": unsupported_service,
            "entity_id": None,
            "entity_type": "service",
            "source_ref": "memory.semantic_contract",
        }
        return _policy_core_handoff_forced_fields(
            intent="out_of_domain",
            reason="unsupported_service_identity_context_requires_admin_handoff",
            subject_kind="service",
            capability="other",
            risk_signals=["unsupported_service", "admin_clarification"],
            slots=slots,
            referents=referents,
        )
    return {
        "intent": "out_of_domain",
        "action": "fact",
        "tool_action_hint": "catalog.service_query",
        "pack_refs": ["services_overview"],
        "slots": {"service": unsupported_service},
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "goal": None,
        "referents": {
            "service": {
                "value": unsupported_service,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "memory.semantic_contract",
            }
        },
        "subject_kind": "service",
        "capability": "other",
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "reason": "unsupported_service_booking_continuation_fact",
    }


def _policy_core_unknown_service_candidate_from_booking_request(
    current_message: str | None,
    *,
    client_slug: str | None,
    grounded_service: str | None,
) -> str | None:
    if isinstance(grounded_service, str) and grounded_service.strip():
        return None
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return None
    has_booking_desire = (
        _policy_core_message_has_pack_signal(
            normalized_message,
            client_slug=client_slug,
            key="booking_desire_keywords",
        )
        or _policy_core_message_has_pack_signal(
            normalized_message,
            client_slug=client_slug,
            key="booking_request",
        )
    )
    if not has_booking_desire:
        return None
    if not _policy_core_current_message_has_message_grounded_temporal_clue(
        normalized_message
    ):
        return None
    cleaned = normalized_message
    exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    if exact_datetime:
        cleaned = cleaned.replace(_normalize_text(exact_datetime) or "", " ")
    cleaned = _POLICY_CORE_EXPLICIT_CLOCK_TIME_PATTERN.sub(" ", cleaned)
    cleaned = _POLICY_CORE_HOUR_TIME_PATTERN.sub(" ", cleaned)
    cleaned = _POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN.sub(" ", cleaned)
    cleaned = _POLICY_CORE_MESSAGE_WEEKDAY_PATTERN.sub(" ", cleaned)
    cleaned = _POLICY_CORE_MESSAGE_NUMERIC_DATE_PATTERN.sub(" ", cleaned)
    cleaned = _POLICY_CORE_MESSAGE_MONTH_DATE_PATTERN.sub(" ", cleaned)
    cleaned = _policy_core_remove_pack_signals(
        cleaned,
        client_slug=client_slug,
        keys=("booking_desire_keywords", "booking_request", "booking_relative_day_keywords"),
    )
    stop_tokens = {
        *_POLICY_CORE_SERVICE_CANDIDATE_RESIDUE_STOP_TOKENS,
        "в",
        "вас",
        "во",
        "маған",
        "мен",
        "мені",
        "меня",
        "мне",
        "нам",
        "нас",
        "сізге",
        "тебя",
    }
    return _policy_core_service_candidate_from_residue(cleaned, stop_tokens=stop_tokens)


def _policy_core_unknown_service_booking_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    client_slug: str | None,
    grounded_service: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile):
        return None
    service_candidate = _policy_core_unknown_service_candidate_from_booking_request(
        current_message,
        client_slug=client_slug,
        grounded_service=grounded_service,
    )
    if not service_candidate:
        return None
    exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    temporal_scope = (
        _policy_core_current_message_grounded_temporal_scope_hint(current_message)
        or "none"
    )
    slots: dict[str, Any] = {"service": service_candidate}
    if exact_datetime:
        slots["datetime"] = exact_datetime
    forced_fields: dict[str, Any] = {
        "intent": "services_overview",
        "action": "fact",
        "tool_action_hint": "catalog.service_query",
        "pack_refs": ["services_overview"],
        "slots": slots,
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "service",
        "capability": "other",
        "temporal_scope": temporal_scope,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "reason": "unsupported_service_booking_request",
        "referents": {
            "service": {
                "value": service_candidate,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "message_candidate",
            }
        },
    }
    if exact_datetime:
        forced_fields["alternate_datetime"] = exact_datetime
    return forced_fields


def _policy_core_contextual_memory_service_exact_datetime_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    client_slug: str | None,
    grounded_service: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile):
        return None
    if isinstance(grounded_service, str) and grounded_service.strip():
        return None
    memory_service = _policy_core_memory_grounded_service(normalized_memory_profile)
    if not memory_service:
        return None
    exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    if not exact_datetime:
        return None
    if not _policy_core_current_message_has_booking_desire_signal(
        current_message,
        client_slug=client_slug,
    ):
        return None
    service_candidate = _policy_core_unknown_service_candidate_from_booking_request(
        current_message,
        client_slug=client_slug,
        grounded_service=grounded_service,
    )
    if service_candidate and not _policy_core_current_message_has_service_modifier_connector(
        current_message
    ):
        return None
    service_value = " ".join(memory_service.split())
    customer_name = _policy_core_memory_customer_name(normalized_memory_profile)
    customer_phone = _policy_core_memory_customer_phone(normalized_memory_profile)
    if customer_name:
        if not customer_phone:
            return _policy_core_collect_phone_forced_fields(
                service_value=service_value,
                datetime_value=exact_datetime,
                customer_name=customer_name,
                service_source_ref="memory.semantic_contract",
                customer_source_ref="memory.slot_state",
                reason="booking_exact_datetime_uses_grounded_memory_service_collect_phone",
            )
        return _policy_core_book_slot_forced_fields(
            service_value=service_value,
            datetime_value=exact_datetime,
            customer_name=customer_name,
            customer_phone=customer_phone,
            source_ref="memory.semantic_contract",
            reason="booking_exact_datetime_uses_grounded_memory_service",
        )
    return _policy_core_collect_name_forced_fields(
        service_value=service_value,
        datetime_value=exact_datetime,
        source_ref="memory.semantic_contract",
        reason="booking_exact_datetime_uses_grounded_memory_service",
    )


def _policy_core_start_booking_partial_datetime_collect_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile):
        return None
    if not isinstance(grounded_service, str) or not grounded_service.strip():
        return None
    if _policy_core_current_message_exact_datetime_surface(current_message):
        return None
    if not _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
        return None
    if not (
        _policy_core_current_message_has_booking_desire_signal(
            current_message,
            client_slug=client_slug,
        )
        or _policy_core_current_message_mentions_grounded_service_value(
            current_message=current_message,
            grounded_service=grounded_service,
        )
    ):
        return None
    temporal_surface = _policy_core_current_message_temporal_clue_surface(current_message)
    if not temporal_surface:
        return None
    service_value = " ".join(grounded_service.split())
    temporal_scope = (
        _policy_core_current_message_grounded_temporal_scope_hint(current_message)
        or "day"
    )
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "slots": {
            "service": service_value,
        },
        "expected_reply_type": "time",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "goal": "booking",
        "referents": {
            "service": _policy_core_service_referent(
                service_value,
                source_ref="message_grounding",
            )
        },
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": temporal_scope,
        "alternate_datetime": temporal_surface,
        "resolution_mode": "direct",
        "pending_question_act": "slot_constraint",
        "pending_question_target": "time",
        "active_question_relation": "slot_constraint",
        "reason": "start_booking_partial_datetime_collect_exact_time",
    }


def _policy_core_active_booking_time_fill_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_loose_booking_time_followup_contract(
        carry_contract,
        normalized_memory_profile,
    ):
        return None
    expected_reply_type = _policy_core_payload_token(carry_contract.get("expected_reply_type"))
    next_question = _policy_core_payload_token(carry_contract.get("next_question"))
    open_questions = _policy_core_expected_open_questions(carry_contract)
    waits_for_exact_time = expected_reply_type == "time" and next_question == "datetime"
    corrects_time_before_name = (
        expected_reply_type == "name"
        and next_question == "name"
        and open_questions == ["name"]
    )
    if not waits_for_exact_time and not corrects_time_before_name:
        return None
    exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    if not exact_datetime:
        return None
    grounded_service = _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return None
    service_value = " ".join(grounded_service.split())
    customer_name = _policy_core_memory_customer_name(normalized_memory_profile)
    customer_phone = _policy_core_current_message_customer_phone_surface(
        current_message
    ) or _policy_core_memory_customer_phone(normalized_memory_profile)
    if customer_name and customer_phone:
        return _policy_core_book_slot_forced_fields(
            service_value=service_value,
            datetime_value=exact_datetime,
            customer_name=customer_name,
            customer_phone=customer_phone,
            source_ref="memory.semantic_contract",
            reason="active_booking_time_fill_ready_for_book_slot",
        )
    if customer_name:
        return _policy_core_collect_phone_forced_fields(
            service_value=service_value,
            datetime_value=exact_datetime,
            customer_name=customer_name,
            service_source_ref="memory.semantic_contract",
            customer_source_ref="memory.slot_state",
            reason="active_booking_time_fill_requires_contact_phone",
        )
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "expected_reply_type": "name",
        "next_question": "name",
        "open_questions": ["name"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": "specific_time",
        "alternate_datetime": exact_datetime,
        "resolution_mode": "direct",
        "slots": {
            "service": service_value,
            "datetime": exact_datetime,
        },
        "referents": {
            "service": {
                "value": service_value,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "memory.semantic_contract",
            }
        },
        "pending_question_act": "fill_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "fill_requested_slot",
    }


def _policy_core_active_booking_partial_datetime_collect_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_loose_booking_time_followup_contract(
        carry_contract,
        normalized_memory_profile,
    ):
        return None
    expected_reply_type = _policy_core_payload_token(carry_contract.get("expected_reply_type"))
    next_question = _policy_core_payload_token(carry_contract.get("next_question"))
    if expected_reply_type != "time" or next_question != "datetime":
        return None
    if _policy_core_current_message_exact_datetime_surface(current_message):
        return None
    if not _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
        return None
    temporal_surface = _policy_core_current_message_temporal_clue_surface(current_message)
    if not temporal_surface:
        return None
    grounded_service = _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return None
    service_value = " ".join(grounded_service.split())
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "slots": {
            "service": service_value,
        },
        "expected_reply_type": "time",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "goal": "booking",
        "referents": {
            "service": _policy_core_service_referent(
                service_value,
                source_ref="memory.semantic_contract",
            )
        },
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": (
            _policy_core_current_message_grounded_temporal_scope_hint(current_message)
            or _policy_core_memory_temporal_scope(normalized_memory_profile)
            or "day"
        ),
        "alternate_datetime": temporal_surface,
        "resolution_mode": "direct",
        "pending_question_act": "slot_constraint",
        "pending_question_target": "time",
        "active_question_relation": "slot_constraint",
        "reason": "active_booking_partial_datetime_slot_constraint",
    }


def _policy_core_active_booking_time_pending_ack_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_loose_booking_time_followup_contract(
        carry_contract,
        normalized_memory_profile,
    ):
        return None
    if not _policy_core_current_message_is_ack_or_confirmation(current_message):
        return None
    if _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
        return None
    service_value = _policy_core_memory_grounded_service(normalized_memory_profile)
    carried_datetime = (
        _policy_core_memory_alternate_datetime(normalized_memory_profile)
        or _policy_core_memory_slot_value(normalized_memory_profile, "datetime")
    )
    if not service_value or not carried_datetime:
        return None
    slots = {
        "service": " ".join(service_value.split()),
        "datetime": carried_datetime,
    }
    customer_name = _policy_core_memory_customer_name(normalized_memory_profile)
    customer_phone = _policy_core_memory_customer_phone(normalized_memory_profile)
    if customer_name:
        slots["name"] = customer_name
    if customer_phone:
        slots["phone"] = customer_phone
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "expected_reply_type": "time",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": _policy_core_memory_temporal_scope(normalized_memory_profile) or "day",
        "alternate_datetime": carried_datetime,
        "resolution_mode": "direct",
        "slots": slots,
        "referents": {
            "service": {
                "value": " ".join(service_value.split()),
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "memory.semantic_contract",
            }
        },
        "pending_question_act": "slot_constraint",
        "pending_question_target": "time",
        "active_question_relation": "slot_constraint",
        "reason": "active_booking_time_pending_ack_still_requires_exact_time",
    }


def _policy_core_active_booking_service_datetime_fill_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_service_choice_followup_contract(
        carry_contract,
        normalized_memory_profile,
    ):
        return None
    exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    if not exact_datetime:
        return None
    service_value = (
        " ".join(grounded_service.split())
        if isinstance(grounded_service, str) and grounded_service.strip()
        else None
    )
    if not service_value:
        return None
    customer_name = _policy_core_current_message_customer_name_surface(
        current_message
    ) or _policy_core_memory_customer_name(normalized_memory_profile)
    customer_phone = _policy_core_current_message_customer_phone_surface(
        current_message
    ) or _policy_core_memory_customer_phone(normalized_memory_profile)
    if customer_name:
        if not customer_phone:
            return _policy_core_collect_phone_forced_fields(
                service_value=service_value,
                datetime_value=exact_datetime,
                customer_name=customer_name,
                service_source_ref="message_grounding",
                customer_source_ref="message_grounding",
                reason="active_booking_service_and_datetime_fill_collect_phone",
            )
        return _policy_core_book_slot_forced_fields(
            service_value=service_value,
            datetime_value=exact_datetime,
            customer_name=customer_name,
            customer_phone=customer_phone,
            source_ref="message_grounding",
            reason="active_booking_service_and_datetime_fill_after_identity",
        )
    return _policy_core_collect_name_forced_fields(
        service_value=service_value,
        datetime_value=exact_datetime,
        source_ref="message_grounding",
        reason="active_booking_service_and_datetime_fill",
    )


def _policy_core_active_booking_service_fill_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    grounded_service: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_service_choice_followup_contract(
        carry_contract,
        normalized_memory_profile,
    ):
        return None
    if not _policy_core_memory_has_datetime_context(normalized_memory_profile):
        return None
    service_value = (
        " ".join(grounded_service.split())
        if isinstance(grounded_service, str) and grounded_service.strip()
        else None
    )
    if not service_value:
        return None
    carried_alternate_datetime = _policy_core_memory_alternate_datetime(
        normalized_memory_profile
    ) or _policy_core_memory_slot_value(normalized_memory_profile, "datetime")
    carried_temporal_scope = (
        _policy_core_memory_temporal_scope(normalized_memory_profile)
        or "specific_time"
    )
    if not carried_alternate_datetime:
        return None
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "expected_reply_type": "name",
        "next_question": "name",
        "open_questions": ["name"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": carried_temporal_scope,
        "alternate_datetime": carried_alternate_datetime,
        "resolution_mode": "direct",
        "slots": {
            "service": service_value,
            "datetime": carried_alternate_datetime,
        },
        "referents": {
            "service": {
                "value": service_value,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "message_grounding",
            }
        },
        "pending_question_act": "fill_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "fill_requested_slot",
    }


def _policy_core_service_choice_slot_carryover_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_service_choice_followup_contract(
        carry_contract,
        normalized_memory_profile,
    ):
        return None
    if isinstance(grounded_service, str) and grounded_service.strip():
        return None
    carried_service = _policy_core_memory_slot_value(
        normalized_memory_profile,
        "service",
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not isinstance(carried_service, str) or not carried_service.strip():
        return None
    service_value = " ".join(carried_service.split())
    if not re.search(r"\b(?:и|and)\b|[,/]", service_value, re.IGNORECASE):
        return None

    memory_datetime = (
        _policy_core_memory_alternate_datetime(normalized_memory_profile)
        or _policy_core_memory_slot_value(normalized_memory_profile, "datetime")
    )
    current_datetime = _policy_core_current_message_exact_datetime_surface(
        current_message
    )
    if not current_datetime and _policy_core_current_message_has_message_grounded_temporal_clue(
        current_message
    ):
        current_temporal = (
            _policy_core_current_message_temporal_context_surface(current_message)
            or _policy_core_normalize_surface_text(current_message)
        )
        current_day_date = _policy_core_day_date_surface(current_temporal)
        memory_day_date = _policy_core_day_date_surface(memory_datetime)
        clock_surface = _policy_core_current_message_clock_like_surface(current_message)
        if clock_surface and not current_day_date and memory_day_date:
            current_datetime = f"{memory_day_date} {clock_surface}"
        elif current_temporal and not current_day_date and memory_day_date:
            current_datetime = f"{memory_day_date} {current_temporal}"
        else:
            current_datetime = current_temporal
    customer_name = _policy_core_current_message_customer_name_surface(
        current_message
    ) or _policy_core_memory_customer_name(normalized_memory_profile)
    customer_phone = _policy_core_current_message_customer_phone_surface(
        current_message
    ) or _policy_core_memory_customer_phone(normalized_memory_profile)
    if not current_datetime and not customer_name and not customer_phone:
        return None

    carried_datetime = current_datetime or memory_datetime
    slots = {"service": service_value}
    if carried_datetime:
        slots["datetime"] = carried_datetime
    if customer_name:
        slots["name"] = customer_name
    if customer_phone:
        slots["phone"] = customer_phone
    temporal_scope = (
        _policy_core_current_message_grounded_temporal_scope_hint(current_message)
        or _policy_core_memory_temporal_scope(normalized_memory_profile)
        or (
            "specific_time"
            if current_datetime
            and _policy_core_current_message_has_explicit_clock_time(current_message)
            else "none"
        )
    )
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "expected_reply_type": "service_choice",
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": temporal_scope,
        "alternate_datetime": carried_datetime,
        "resolution_mode": "clarify_missing_subject",
        "slots": slots,
        "referents": {
            "service": {
                "value": service_value,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "memory.slot_state",
            }
        },
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "reason": "service_choice_pending_preserve_non_service_slots",
    }


def _policy_core_current_message_has_specialist_relaxation_signal(
    current_message: str | None,
    *,
    client_slug: str | None,
) -> bool:
    if not isinstance(current_message, str) or not current_message.strip():
        return False
    has_master_signal = bool(
        _policy_core_current_message_has_master_query_signal(
            current_message,
            client_slug=client_slug,
        )
        or _policy_core_message_has_pack_signal(
            current_message,
            client_slug=client_slug,
            key="info_master_keywords",
        )
        or _policy_core_message_has_pack_signal(
            current_message,
            client_slug=client_slug,
            key="master_query_person_terms",
        )
    )
    if not has_master_signal:
        return False
    return _policy_core_message_has_pack_signal(
        current_message,
        client_slug=client_slug,
        key="specialist_relaxation_keywords",
    )


def _policy_core_specialist_relaxation_collect_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if _policy_core_payload_token(carry_contract.get("expected_reply_type")) != "name":
        return None
    if _policy_core_payload_token(carry_contract.get("next_question")) != "name":
        return None
    if _policy_core_expected_open_questions(carry_contract) != ["name"]:
        return None
    if not _policy_core_current_message_has_specialist_relaxation_signal(
        current_message,
        client_slug=client_slug,
    ):
        return None
    grounded_service = _policy_core_memory_grounded_service(normalized_memory_profile)
    carried_alternate_datetime = _policy_core_memory_alternate_datetime(
        normalized_memory_profile
    )
    carried_temporal_scope = (
        _policy_core_memory_temporal_scope(normalized_memory_profile)
        or "specific_time"
    )
    if not grounded_service or not carried_alternate_datetime:
        return None
    return _policy_core_collect_name_forced_fields(
        service_value=" ".join(grounded_service.split()),
        datetime_value=carried_alternate_datetime,
        temporal_scope=carried_temporal_scope,
        source_ref="memory.semantic_contract",
        reason="specialist_preference_relaxed_resume_customer_name_collect",
    )


def _policy_core_resolve_active_booking_info_interrupt_variant(
    *,
    current_message: str | None,
    client_slug: str | None,
) -> PolicyCoreBookingInfoInterruptVariantV1 | None:
    service_multifact_refs = _policy_core_current_message_service_multifact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if service_multifact_refs == ["pricing", "duration"]:
        return resolve_policy_core_booking_info_interrupt_variant(
            intent="pricing",
            capability="pricing",
            pack_refs=("pricing", "duration"),
            family="active_continuity",
        )
    if _policy_core_current_message_has_promotions_query(current_message):
        return resolve_policy_core_booking_info_interrupt_variant(
            intent="promotions",
            capability="promotions",
            pack_refs=("promotions",),
            family="active_continuity",
        )
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return None
    from app.services.pack_runtime_service import get_pack_runtime

    try:
        pack_runtime = get_pack_runtime(client_slug)
    except Exception:
        pack_runtime = None
    if pack_runtime is None:
        return None
    try:
        if pack_runtime.has_duration_signal(normalized_message, message=current_message):
            return resolve_policy_core_booking_info_interrupt_variant(
                intent="duration",
                capability="duration",
                pack_refs=("duration",),
                family="active_continuity",
            )
    except Exception:
        pass
    try:
        if pack_runtime.has_price_signal(normalized_message, message=current_message):
            return resolve_policy_core_booking_info_interrupt_variant(
                intent="pricing",
                capability="pricing",
                pack_refs=("pricing",),
                family="active_continuity",
            )
    except Exception:
        pass
    if _policy_core_current_message_has_master_query_signal(
        current_message,
        client_slug=client_slug,
    ):
        return resolve_policy_core_booking_info_interrupt_variant(
            intent="master_query",
            capability="master",
            pack_refs=("master",),
            family="active_continuity",
        )
    return None


def _policy_core_active_booking_info_interrupt_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_loose_booking_time_followup_contract(
        carry_contract,
        normalized_memory_profile,
    ):
        return None
    if _policy_core_current_message_exact_datetime_surface(current_message):
        return None
    service_value = (
        " ".join(grounded_service.split())
        if isinstance(grounded_service, str) and grounded_service.strip()
        else _policy_core_memory_grounded_service(normalized_memory_profile)
    )
    if not service_value:
        return None
    variant = _policy_core_resolve_active_booking_info_interrupt_variant(
        current_message=current_message,
        client_slug=client_slug,
    )
    if variant is None:
        return None
    expected_reply_type = _policy_core_payload_token(carry_contract.get("expected_reply_type"))
    next_question = _policy_core_payload_token(carry_contract.get("next_question"))
    if not expected_reply_type or not next_question:
        return None
    pending_question_act = (
        _policy_core_payload_token(carry_contract.get("pending_question_act"))
        or "ask_about_requested_slot"
    )
    pending_question_target = (
        _policy_core_payload_token(carry_contract.get("pending_question_target"))
        or "time"
    )
    subject_kind = (
        "general" if variant.tool_action_hint == "catalog.location" else "service"
    )
    slots = {"service": service_value} if subject_kind == "service" else {}
    referents = (
        {
            "service": {
                "value": service_value,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "memory.semantic_contract",
            }
        }
        if subject_kind == "service"
        else {}
    )
    return {
        "intent": variant.head_intent,
        "action": "fact",
        "tool_action_hint": variant.tool_action_hint,
        "pack_refs": list(variant.pack_refs),
        "slots": slots,
        "expected_reply_type": expected_reply_type,
        "next_question": next_question,
        "open_questions": _policy_core_expected_open_questions(carry_contract),
        "needs_manager": False,
        "goal": "booking",
        "referents": referents,
        "subject_kind": subject_kind,
        "capability": variant.capability,
        "temporal_scope": _policy_core_memory_temporal_scope(normalized_memory_profile) or "none",
        "alternate_datetime": _policy_core_memory_alternate_datetime(normalized_memory_profile),
        "resolution_mode": "policy_fact",
        "pending_question_act": pending_question_act,
        "pending_question_target": pending_question_target,
        "active_question_relation": "generic_info_interrupt",
    }


def _policy_core_booking_availability_missing_service_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(normalized_memory_profile) or _policy_core_active_pending_contract(
        normalized_memory_profile
    ):
        return None
    if not isinstance(current_message, str) or not current_message.strip():
        return None
    normalized_message = " ".join(current_message.split())
    if not any(
        pattern.search(normalized_message)
        for pattern in _POLICY_CORE_GENERIC_AVAILABILITY_QUERY_PATTERNS
    ):
        return None
    if not _policy_core_current_message_has_message_grounded_temporal_clue(
        normalized_message
    ):
        return None
    grounded_service_hint = _policy_core_resolve_current_message_service_hint(
        current_message=normalized_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    if grounded_service_hint:
        return None
    exact_datetime = _policy_core_current_message_exact_datetime_surface(normalized_message)
    if not exact_datetime:
        return None
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "slots": {"datetime": exact_datetime},
        "expected_reply_type": "service_choice",
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "general",
        "capability": "bookability",
        "temporal_scope": "specific_time",
        "alternate_datetime": exact_datetime,
        "resolution_mode": "clarify_missing_subject",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
    }


def _policy_core_narrow_start_booking_exact_datetime_owner_envelope(
    allowed_payload: Mapping[str, Any],
    context_payload: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    narrowed_allowed = dict(allowed_payload)
    narrowed_allowed["info_refs"] = []
    narrowed_allowed["consult_refs"] = []
    raw_tool_actions = [
        action
        for action in list(narrowed_allowed.get("tool_actions") or [])
        if isinstance(action, str) and action.strip()
    ]
    narrowed_allowed["tool_actions"] = [
        action for action in ("collect", "handoff") if action in raw_tool_actions
    ]
    narrowed_context = dict(context_payload) if isinstance(context_payload, Mapping) else {}
    narrowed_context.pop("consult_cards", None)
    return narrowed_allowed, narrowed_context or None


def _policy_core_active_booking_commit_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if _policy_core_payload_token(carry_contract.get("expected_reply_type")) != "name":
        return None
    if _policy_core_payload_token(carry_contract.get("next_question")) != "name":
        return None
    if _policy_core_expected_open_questions(carry_contract) != ["name"]:
        return None
    customer_name = _policy_core_current_message_customer_name_surface(current_message)
    if not customer_name:
        return None
    if not _policy_core_memory_grounded_service(normalized_memory_profile):
        return None
    grounded_service = _policy_core_memory_grounded_service(normalized_memory_profile)
    carried_alternate_datetime = _policy_core_memory_alternate_datetime(
        normalized_memory_profile
    )
    carried_temporal_scope = _policy_core_memory_temporal_scope(
        normalized_memory_profile
    )
    if not carried_alternate_datetime or carried_temporal_scope != "specific_time":
        return None
    slots = {
        "service": grounded_service,
        "datetime": carried_alternate_datetime,
        "name": customer_name,
    }
    customer_phone = _policy_core_current_message_customer_phone_surface(current_message)
    if customer_phone:
        slots["phone"] = customer_phone
    else:
        return _policy_core_collect_phone_forced_fields(
            service_value=grounded_service,
            datetime_value=carried_alternate_datetime,
            customer_name=customer_name,
            temporal_scope=carried_temporal_scope,
            service_source_ref="memory.semantic_contract",
            customer_source_ref="message_grounding",
            reason="active_booking_name_fill_requires_contact_phone",
        )
    return {
        "intent": "booking",
        "action": "fact",
        "tool_action_hint": "calendar.book_slot",
        "pack_refs": [],
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": carried_temporal_scope,
        "alternate_datetime": carried_alternate_datetime,
        "resolution_mode": "live_calendar",
        "slots": slots,
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
    }


def _policy_core_is_booking_phone_followup_contract(
    contract_payload: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(contract_payload, Mapping):
        return False
    expected_reply_type = _policy_core_payload_token(contract_payload.get("expected_reply_type"))
    next_question = _policy_core_payload_token(contract_payload.get("next_question"))
    open_questions = set(_policy_core_expected_open_questions(contract_payload))
    return bool(
        expected_reply_type == "phone"
        or next_question == "phone"
        or "phone" in open_questions
    )


def _policy_core_active_booking_phone_fill_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> dict[str, Any] | None:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_phone_followup_contract(carry_contract):
        return None
    grounded_service = _policy_core_memory_grounded_service(normalized_memory_profile)
    carried_datetime = (
        _policy_core_memory_alternate_datetime(normalized_memory_profile)
        or _policy_core_memory_slot_value(normalized_memory_profile, "datetime")
    )
    customer_name = _policy_core_memory_customer_name(normalized_memory_profile)
    if not grounded_service or not carried_datetime or not customer_name:
        return None
    service_value = " ".join(grounded_service.split())
    datetime_value = " ".join(carried_datetime.split())
    customer_phone = _policy_core_current_message_customer_phone_surface(current_message)
    if customer_phone:
        return _policy_core_book_slot_forced_fields(
            service_value=service_value,
            datetime_value=datetime_value,
            customer_name=customer_name,
            customer_phone=customer_phone,
            source_ref="memory.semantic_contract",
            reason="active_booking_phone_fill_ready_for_book_slot",
        )
    if _policy_core_current_message_has_contact_delay_signal(current_message):
        return _policy_core_collect_phone_forced_fields(
            service_value=service_value,
            datetime_value=datetime_value,
            customer_name=customer_name,
            temporal_scope=_policy_core_memory_temporal_scope(normalized_memory_profile)
            or "specific_time",
            service_source_ref="memory.semantic_contract",
            customer_source_ref="memory.slot_state",
            reason="active_booking_phone_fill_contact_delayed",
        )
    return None


def _build_policy_core_focused_contract_retry_instruction(
    forced_fields: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(forced_fields, Mapping) or not forced_fields:
        return None
    canonical_contract = json.dumps(
        dict(forced_fields),
        ensure_ascii=False,
        sort_keys=True,
    )
    return (
        "Предыдущая structured-output попытка вернула пустой ответ. "
        "Верни ровно один JSON-объект без markdown и без пояснений. "
        "Сохрани эти поля точно как указано и не меняй их значения: "
        f"{canonical_contract}. "
        "Остальные поля заполняй только если они подтверждаются текущим "
        "сообщением и carryover-контекстом."
    )


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


_POLICY_CORE_FOCUSED_PROMPT = """# LLM Policy Core Focused Contract

Ты LLM Policy Core. Верни ТОЛЬКО JSON без markdown и текста вне JSON.
Ты остаёшься единственным semantic owner хода.

Вход содержит `focus_contract.forced_fields`. Это governed owner contract, построенный из текущего сообщения, памяти, pack/runtime context и capability rules.

Правила:
- Верни JSON, который строго соответствует response_format schema.
- Скопируй значения из `focus_contract.forced_fields` точно, без переименования и без смысловой замены.
- Не добавляй business facts в ответ: факты выполняются через tool/pack path после owner boundary.
- Не придумывай service/specialist/customer/date вне входного envelope.
- Если schema содержит только focused fields, верни только эти fields.
"""



def _build_policy_core_messages(prompt: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _build_policy_core_focused_input(
    policy_input: dict[str, Any],
    forced_fields: Mapping[str, Any],
) -> dict[str, Any]:
    focused_input = _build_policy_core_compact_input(policy_input)
    allowed_payload = focused_input.get("allowed")
    if isinstance(allowed_payload, dict):
        normalized_allowed = dict(allowed_payload)
        forced_tool_action = forced_fields.get("tool_action_hint")
        if isinstance(forced_tool_action, str) and forced_tool_action.strip():
            normalized_allowed["tool_actions"] = [forced_tool_action.strip()]
        forced_pack_refs = forced_fields.get("pack_refs")
        if isinstance(forced_pack_refs, list):
            normalized_allowed["info_refs"] = [
                item for item in forced_pack_refs if isinstance(item, str) and item.strip()
            ]
        normalized_allowed["consult_refs"] = []
        focused_input["allowed"] = normalized_allowed
    focused_input.pop("context", None)
    focused_input["focus_contract"] = {
        "forced_fields": deepcopy(dict(forced_fields)),
    }
    return focused_input


def _policy_core_focused_empty_extra(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _policy_core_focused_forced_field_mismatch(
    actual: Any,
    expected: Any,
    *,
    path: str,
) -> str | None:
    if isinstance(expected, Mapping):
        if not expected and actual is None:
            return None
        if not isinstance(actual, Mapping):
            return path
        for key, expected_value in expected.items():
            if path.startswith("referents.") and key in {"entity_id", "source_ref"}:
                continue
            if key not in actual:
                return f"{path}.{key}"
            mismatch = _policy_core_focused_forced_field_mismatch(
                actual.get(key),
                expected_value,
                path=f"{path}.{key}",
            )
            if mismatch:
                return mismatch
        for key, actual_value in actual.items():
            if path.startswith("referents.") and key in {"entity_id", "source_ref"}:
                continue
            if key not in expected and not _policy_core_focused_empty_extra(actual_value):
                return f"{path}.{key}"
        return None
    if isinstance(expected, list):
        if not expected and actual is None:
            return None
        if not isinstance(actual, list):
            return path
        if actual != expected:
            return path
        return None
    if actual != expected:
        return path
    return None


def _policy_core_focused_contract_error(
    payload: Mapping[str, Any] | None,
    forced_fields: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping) or not isinstance(forced_fields, Mapping):
        return None
    for key, expected_value in forced_fields.items():
        if key not in payload:
            if _policy_core_focused_empty_extra(expected_value):
                continue
            return f"llm_policy_core_error:focused_contract_mismatch:{key}"
        mismatch = _policy_core_focused_forced_field_mismatch(
            payload.get(key),
            expected_value,
            path=key,
        )
        if mismatch:
            return f"llm_policy_core_error:focused_contract_mismatch:{mismatch}"
    return None


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
    pending_contract = _policy_core_resume_pending_contract(memory_profile) or _policy_core_active_pending_contract(
        memory_profile
    )
    if not pending_contract:
        return False
    expected_reply_type = _policy_core_payload_token(
        pending_contract.get("expected_reply_type")
    )
    if not expected_reply_type:
        return False
    if expected_reply_type == "media":
        return False
    active_goal = _policy_core_payload_token(memory_profile.get("active_goal"))
    capability = None
    semantic_contract = memory_profile.get("semantic_contract")
    if isinstance(semantic_contract, dict):
        capability = _policy_core_payload_token(semantic_contract.get("capability"))
        if capability in {"bookability", "booking_manage"}:
            # Governed booking continuity is the current single-owner hot path.
            # Keep it on the canonical full prompt so compact fallback cannot
            # silently drift booking progression or existing-booking lookup axes.
            return False
    if active_goal == "booking":
        next_question = _policy_core_payload_token(pending_contract.get("next_question"))
        pending_target = _policy_core_payload_token(
            pending_contract.get("pending_question_target")
        )
        pending_act = _policy_core_payload_token(pending_contract.get("pending_question_act"))
        active_relation = _policy_core_payload_token(
            pending_contract.get("active_question_relation")
        )
        if next_question in {"datetime", "service", "name"} and (
            pending_target in {"time", "specialist"}
            or pending_act
            in {
                "ask_about_requested_slot",
                "slot_constraint",
                "fill_requested_slot",
                "referent_followup",
            }
            or active_relation in {"generic_info_interrupt", "referent_followup"}
        ):
            # Owner-backed booking follow-up must stay on the full prompt even
            # after a fact-side interrupt, otherwise compact-first retries can
            # mask raw-owner quality on the resume turn.
            return False
    return True


def _policy_core_current_message_has_master_query_signal(
    current_message: str | None,
    *,
    client_slug: str | None,
) -> bool:
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return False
    if _policy_core_message_has_pack_signal(
        current_message,
        client_slug=client_slug,
        key="info_master_keywords",
    ):
        return True
    if _policy_core_message_has_pack_signal(
        current_message,
        client_slug=client_slug,
        key="master_query_direct_terms",
    ):
        return True
    has_person = _policy_core_message_has_pack_signal(
        current_message,
        client_slug=client_slug,
        key="master_query_person_terms",
    )
    if not has_person:
        return False
    return bool(
        _policy_core_message_has_pack_signal(
            current_message,
            client_slug=client_slug,
            key="master_query_action_terms",
        )
        or _policy_core_message_has_pack_signal(
            current_message,
            client_slug=client_slug,
            key="master_query_relation_terms",
        )
    )


def _policy_core_blocks_compact_first_attempt(
    memory_profile: dict[str, Any] | None,
    *,
    current_message: str | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_current_message_has_temporal_booking_side_ask(current_message):
        if not isinstance(memory_profile, dict) or not memory_profile:
            return False
        grounded_service_hint = _policy_core_resolve_current_message_service_hint(
            current_message=current_message,
            context_payload=None,
            client_slug=client_slug,
        )
        if grounded_service_hint:
            return False
    if not isinstance(memory_profile, dict):
        return False
    pending_contract = _policy_core_resume_pending_contract(memory_profile) or _policy_core_active_pending_contract(
        memory_profile
    )
    if not pending_contract:
        return False
    expected_reply_type = _policy_core_payload_token(
        pending_contract.get("expected_reply_type")
    )
    if expected_reply_type == "media":
        return True
    capability = None
    semantic_contract = memory_profile.get("semantic_contract")
    if isinstance(semantic_contract, dict):
        capability = _policy_core_payload_token(semantic_contract.get("capability"))
        if capability == "booking_manage":
            # Booking-manage reference turns are stable on the canonical full prompt
            # and do not benefit from compact-first routing.
            return True
    if _policy_core_current_message_has_master_query_signal(
        current_message,
        client_slug=client_slug,
    ):
        # Master/specialist continuity rows are the current compact-first outlier:
        # they stay clean on the full prompt but can drift across relation/pack-ref
        # axes under compact-first retries.
        return True
    active_goal = _policy_core_payload_token(memory_profile.get("active_goal"))
    if active_goal != "booking":
        return False
    next_question = _policy_core_payload_token(pending_contract.get("next_question"))
    if next_question not in {"datetime", "service", "name"}:
        return False
    if capability in {"bookability", "live_availability"}:
        return True
    pending_target = _policy_core_payload_token(
        pending_contract.get("pending_question_target")
    )
    pending_act = _policy_core_payload_token(pending_contract.get("pending_question_act"))
    active_relation = _policy_core_payload_token(
        pending_contract.get("active_question_relation")
    )
    return (
        pending_target in {"time", "specialist"}
        or pending_act
        in {
            "ask_about_requested_slot",
            "slot_constraint",
            "fill_requested_slot",
            "referent_followup",
        }
        or active_relation in {"generic_info_interrupt", "referent_followup"}
    )


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
    raw_entity_refs = sanitized_payload.get("entity_refs")
    if isinstance(raw_entity_refs, dict):
        normalized_entity_refs: list[dict[str, Any]] = []
        for entity_type, value in raw_entity_refs.items():
            if not isinstance(entity_type, str) or not entity_type.strip():
                continue
            if not isinstance(value, str) or not value.strip():
                continue
            normalized_entity_refs.append(
                {
                    "entity_type": entity_type.strip(),
                    "value": value.strip(),
                    "source_ref": "entity_refs",
                }
            )
        sanitized_payload["entity_refs"] = normalized_entity_refs
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


def _policy_core_datetime_parse_candidates(value: str) -> list[str]:
    raw_value = value.strip()
    if not raw_value:
        return []
    candidates = [raw_value]
    lowered = raw_value.casefold()
    for prefix in ("на ", "в ", "во ", "к ", "ко "):
        if lowered.startswith(prefix) and len(raw_value) > len(prefix):
            candidates.append(raw_value[len(prefix) :].strip())
            break
    for candidate in tuple(candidates):
        normalized_candidate = _POLICY_CORE_CLOCK_TIME_PREPOSITION_PATTERN.sub(
            "",
            candidate,
        ).strip()
        if normalized_candidate and normalized_candidate not in candidates:
            candidates.append(normalized_candidate)
    return candidates


def _policy_core_booking_datetime_surface_is_executable(value: Any) -> bool:
    normalized = _policy_core_normalize_surface_text(value)
    if not normalized:
        return False
    if _policy_core_current_message_has_explicit_clock_time(normalized) and any(
        pattern.search(normalized)
        for pattern in (
            _POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN,
            _POLICY_CORE_MESSAGE_WEEKDAY_PATTERN,
            _POLICY_CORE_MESSAGE_NUMERIC_DATE_PATTERN,
            _POLICY_CORE_MESSAGE_MONTH_DATE_PATTERN,
        )
    ):
        return True
    for candidate in _policy_core_datetime_parse_candidates(normalized):
        try:
            datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            return True
        except ValueError:
            pass
    return False



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


def _policy_core_is_loose_booking_time_followup_contract(
    contract_payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if _policy_core_is_booking_time_followup_contract(contract_payload):
        return True
    if not isinstance(contract_payload, Mapping):
        return False
    if _policy_core_payload_token(normalized_memory_profile.get("active_goal") if isinstance(normalized_memory_profile, Mapping) else None) != "booking":
        return False
    expected_reply_type = _policy_core_payload_token(contract_payload.get("expected_reply_type"))
    next_question = _policy_core_payload_token(contract_payload.get("next_question"))
    open_questions = set(_policy_core_expected_open_questions(contract_payload))
    return bool(
        expected_reply_type == "time"
        and next_question == "datetime"
        and ("datetime" in open_questions or not open_questions)
    )


def _policy_core_is_booking_service_choice_followup_contract(
    contract_payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(contract_payload, Mapping):
        return False
    if _policy_core_payload_token(normalized_memory_profile.get("active_goal") if isinstance(normalized_memory_profile, Mapping) else None) != "booking":
        return False
    expected_reply_type = _policy_core_payload_token(contract_payload.get("expected_reply_type"))
    next_question = _policy_core_payload_token(contract_payload.get("next_question"))
    open_questions = set(_policy_core_expected_open_questions(contract_payload))
    return bool(
        expected_reply_type == "service_choice"
        or next_question == "service"
        or "service" in open_questions
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
        or _POLICY_CORE_SPLIT_CLOCK_TIME_PATTERN.search(normalized)
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


def _policy_core_day_date_surface(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    for pattern in (
        _POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN,
        _POLICY_CORE_MESSAGE_WEEKDAY_PATTERN,
        _POLICY_CORE_MESSAGE_NUMERIC_DATE_PATTERN,
        _POLICY_CORE_MESSAGE_MONTH_DATE_PATTERN,
    ):
        match = pattern.search(normalized)
        if match is not None:
            return match.group(0).strip()
    return None


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


def _policy_core_current_message_is_ack_or_confirmation(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split()).strip()
    if not normalized:
        return False
    if _POLICY_CORE_ACK_OR_CONFIRMATION_ONLY_PATTERN.fullmatch(normalized):
        return True
    return _policy_core_message_has_pack_signal(
        normalized,
        client_slug=None,
        key="booking_confirmation_keywords",
    )


def _policy_core_current_message_has_customer_name_non_identity_signal(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str) or not current_message.strip():
        return False
    return any(
        _policy_core_message_has_pack_signal(
            current_message,
            client_slug=None,
            key=signal_key,
        )
        for signal_key in _POLICY_CORE_CUSTOMER_NAME_NON_IDENTITY_SIGNAL_KEYS
    )


def _policy_core_current_message_has_contact_delay_signal(
    current_message: str | None,
) -> bool:
    return _policy_core_message_has_pack_signal(
        current_message,
        client_slug=None,
        key="contact_delay_keywords",
    )


def _policy_core_remove_customer_name_non_identity_signals(
    value: str,
) -> str:
    cleaned = _policy_core_remove_pack_signals(
        value,
        client_slug=None,
        keys=_POLICY_CORE_CUSTOMER_NAME_NON_IDENTITY_SIGNAL_KEYS,
    )
    cleaned = _POLICY_CORE_CUSTOMER_NAME_PRONOUN_PATTERN.sub(" ", cleaned)
    return " ".join(cleaned.split()).strip(" \t\r\n.,!?;:-")


def _policy_core_current_message_can_fill_customer_name(
    current_message: str | None,
) -> bool:
    if _policy_core_current_message_has_explicit_customer_name_intro(current_message):
        return True
    if not isinstance(current_message, str):
        return False
    normalized = _policy_core_strip_current_message_contact_surface(
        " ".join(current_message.split())
    ).strip(" \t\r\n.,!?;:")
    if not normalized or len(normalized) > 80:
        return False
    if _policy_core_current_message_is_ack_or_confirmation(normalized):
        return False
    if _policy_core_current_message_has_customer_name_non_identity_signal(normalized):
        return False
    if "?" in normalized or _policy_core_current_message_has_message_grounded_temporal_clue(
        normalized
    ):
        return False
    if _policy_core_current_message_has_explicit_clock_time(normalized):
        return False
    if re.search(r"\d", normalized):
        return False
    if re.search(r"[^A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә'’\-\s.]", normalized):
        return False
    tokens = re.findall(
        r"[A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә][A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә'’\-]*",
        normalized,
    )
    return 1 <= len(tokens) <= 3


def _policy_core_current_message_customer_name_surface(
    current_message: str | None,
) -> str | None:
    if not _policy_core_current_message_can_fill_customer_name(current_message):
        return None
    if not isinstance(current_message, str):
        return None
    normalized = _policy_core_strip_current_message_contact_surface(
        " ".join(current_message.split())
    ).strip(" \t\r\n.,!?;:")
    if not normalized:
        return None
    for pattern in _POLICY_CORE_EXPLICIT_CUSTOMER_NAME_INTRO_PATTERNS:
        if pattern.pattern.startswith("^\\s*"):
            continue
        normalized = pattern.sub("", normalized, count=1).strip(" \t\r\n.,!?;:-")
    normalized = _POLICY_CORE_CONTACT_LABEL_PATTERN.sub(" ", normalized).strip(" \t\r\n.,!?;:-")
    normalized = re.sub(r"^\s*(?:я|мен)\s+", "", normalized, flags=re.IGNORECASE)
    normalized = _POLICY_CORE_CUSTOMER_NAME_PRONOUN_PATTERN.sub(" ", normalized)
    normalized = _policy_core_remove_customer_name_non_identity_signals(normalized)
    normalized = " ".join(normalized.split()).strip(" \t\r\n.,!?;:-")
    tokens = re.findall(
        r"[A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә][A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә'’\-]*",
        normalized,
    )
    if not 1 <= len(tokens) <= 3:
        return None
    return " ".join(tokens)


def _policy_core_current_message_customer_phone_surface(
    current_message: str | None,
) -> str | None:
    if not isinstance(current_message, str):
        return None
    normalized = " ".join(current_message.split())
    if not normalized:
        return None
    match = _POLICY_CORE_PHONE_SURFACE_PATTERN.search(normalized)
    if match is None:
        return None
    phone_surface = match.group("phone")
    digits = re.sub(r"\D", "", phone_surface)
    if not 7 <= len(digits) <= 15:
        return None
    return f"+{digits}" if phone_surface.lstrip().startswith("+") else digits


def _policy_core_memory_customer_name_surface_is_valid(value: str | None) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if _policy_core_current_message_has_customer_name_non_identity_signal(value):
        return False
    return _policy_core_current_message_customer_name_surface(value) is not None


def _policy_core_current_message_inline_customer_name_surface(
    *,
    current_message: str | None,
    service_value: str | None,
    exact_datetime: str | None,
    client_slug: str | None,
) -> str | None:
    if not isinstance(current_message, str) or not current_message.strip():
        return None
    normalized = _policy_core_strip_current_message_contact_surface(
        " ".join(current_message.split())
    )
    if not normalized:
        return None
    if isinstance(exact_datetime, str) and exact_datetime.strip():
        normalized = re.sub(
            re.escape(" ".join(exact_datetime.split())),
            " ",
            normalized,
            count=1,
            flags=re.IGNORECASE,
        )
    normalized = _POLICY_CORE_EXPLICIT_CLOCK_TIME_PATTERN.sub(" ", normalized)
    normalized = _POLICY_CORE_HOUR_TIME_PATTERN.sub(" ", normalized)
    normalized = _POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN.sub(" ", normalized)
    normalized = _POLICY_CORE_MESSAGE_WEEKDAY_PATTERN.sub(" ", normalized)
    normalized = _POLICY_CORE_MESSAGE_NUMERIC_DATE_PATTERN.sub(" ", normalized)
    normalized = _POLICY_CORE_MESSAGE_MONTH_DATE_PATTERN.sub(" ", normalized)
    if isinstance(service_value, str) and service_value.strip():
        normalized_service = " ".join(service_value.split())
        normalized = re.sub(
            rf"(?<!\w){re.escape(normalized_service)}(?!\w)",
            " ",
            normalized,
            flags=re.IGNORECASE,
        )
    normalized = _policy_core_remove_pack_signals(
        normalized,
        client_slug=client_slug,
        keys=("booking_desire_keywords", "booking_request", "booking_relative_day_keywords"),
    )
    normalized = re.sub(r"[^A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә'’\-\s]", " ", normalized)
    stop_tokens = {
        "а",
        "в",
        "во",
        "еще",
        "ещё",
        "и",
        "к",
        "ко",
        "мен",
        "меня",
        "маған",
        "мені",
        "мне",
        "на",
        "нам",
        "нас",
        "пожалуйста",
        "раз",
        "с",
        "со",
        "сізге",
        "тебя",
        "хочу",
        "вас",
    }
    tokens = [
        token
        for token in re.findall(
            r"[A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә][A-Za-zА-Яа-яЁёҚқҒғҢңӨөҰұҮүҺһІіӘә'’\-]*",
            normalized,
        )
        if token.casefold() not in stop_tokens
    ]
    if not 1 <= len(tokens) <= 3:
        return None
    return " ".join(tokens)


def _policy_core_strip_current_message_contact_surface(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    without_phone = _POLICY_CORE_PHONE_SURFACE_PATTERN.sub(" ", value)
    without_labels = _POLICY_CORE_CONTACT_LABEL_PATTERN.sub(" ", without_phone)
    without_separators = re.sub(r"[,;:]+", " ", without_labels)
    return " ".join(without_separators.split())


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
    if _POLICY_CORE_MESSAGE_NUMERIC_DATE_PATTERN.search(
        normalized
    ) or _POLICY_CORE_MESSAGE_MONTH_DATE_PATTERN.search(normalized):
        return "day"
    return None


def _policy_core_current_message_temporal_clue_surface(
    current_message: str | None,
) -> str | None:
    exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    if exact_datetime:
        return exact_datetime
    if not isinstance(current_message, str):
        return None
    normalized = " ".join(current_message.split())
    if not normalized:
        return None
    starts = [
        match.start()
        for pattern in (
            _POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN,
            _POLICY_CORE_MESSAGE_WEEKDAY_PATTERN,
            _POLICY_CORE_MESSAGE_NUMERIC_DATE_PATTERN,
            _POLICY_CORE_MESSAGE_MONTH_DATE_PATTERN,
            *_POLICY_CORE_MESSAGE_GROUNDED_TEMPORAL_CLUE_PATTERNS,
        )
        for match in [pattern.search(normalized)]
        if match is not None
    ]
    if not starts:
        return None
    surface = normalized[min(starts):].strip(" ,.!?:;")
    return surface or None


def _policy_core_current_message_temporal_context_surface(
    current_message: str | None,
) -> str | None:
    if not isinstance(current_message, str):
        return None
    normalized = " ".join(current_message.split())
    if not normalized:
        return None
    starts = [
        match.start()
        for pattern in (
            _POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN,
            _POLICY_CORE_MESSAGE_WEEKDAY_PATTERN,
            _POLICY_CORE_MESSAGE_NUMERIC_DATE_PATTERN,
            _POLICY_CORE_MESSAGE_MONTH_DATE_PATTERN,
            _POLICY_CORE_EXPLICIT_CLOCK_TIME_PATTERN,
            _POLICY_CORE_HOUR_TIME_PATTERN,
            *_POLICY_CORE_MESSAGE_GROUNDED_TEMPORAL_CLUE_PATTERNS,
        )
        for match in [pattern.search(normalized)]
        if match is not None
    ]
    if not starts:
        return None
    surface = normalized[min(starts):].strip(" ,.!?:;")
    return surface or None


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
        or _POLICY_CORE_MESSAGE_MONTH_DATE_PATTERN.search(normalized)
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
            _POLICY_CORE_MESSAGE_MONTH_DATE_PATTERN,
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
    split_clock_match = _POLICY_CORE_SPLIT_CLOCK_TIME_PATTERN.search(surface)
    if split_clock_match is not None:
        return surface[: split_clock_match.end()].strip(" ,.!?;:")
    hour_match = _POLICY_CORE_HOUR_TIME_PATTERN.search(surface)
    if hour_match is not None:
        return surface[: hour_match.end()].strip(" ,.!?;:")
    return surface.strip(" ,.!?:") or None


def _policy_core_current_message_clock_time_surface(
    current_message: str | None,
) -> str | None:
    if not isinstance(current_message, str):
        return None
    normalized = " ".join(current_message.split())
    if not normalized:
        return None
    match = _POLICY_CORE_EXPLICIT_CLOCK_TIME_PATTERN.search(normalized)
    if match is None:
        return None
    return match.group(0).strip() or None


def _policy_core_current_message_clock_like_surface(
    current_message: str | None,
) -> str | None:
    if not isinstance(current_message, str):
        return None
    normalized = " ".join(current_message.split())
    if not normalized:
        return None
    for pattern in (
        _POLICY_CORE_EXPLICIT_CLOCK_TIME_PATTERN,
        _POLICY_CORE_SPLIT_CLOCK_TIME_PATTERN,
        _POLICY_CORE_HOUR_TIME_PATTERN,
    ):
        match = pattern.search(normalized)
        if match is not None:
            return match.group(0).strip()
    return None


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
        if _policy_core_current_message_has_master_query_signal(
            current_message,
            client_slug=client_slug,
        ):
            refs.append("master")
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


def _policy_core_current_message_hours_service_booking_followup_pack_refs(
    current_message: str | None,
    *,
    client_slug: str | None = None,
) -> list[str] | None:
    expected_pack_refs = _policy_core_current_message_hours_service_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return None
    if _policy_core_current_message_has_location_side_ask(current_message):
        return None
    if not _policy_core_current_message_has_temporal_booking_side_ask(current_message):
        return None
    normalized_pack_refs = {
        item.strip().casefold()
        for item in expected_pack_refs
        if isinstance(item, str) and item.strip()
    }
    if "promotions" in normalized_pack_refs or "master" in normalized_pack_refs:
        return None
    if not normalized_pack_refs.intersection({"pricing", "duration", "services_overview"}):
        return None
    return expected_pack_refs


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
        if _policy_core_current_message_has_master_query_signal(
            current_message,
            client_slug=client_slug,
        ):
            refs.append("master")
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


def _policy_core_current_message_hours_location_booking_followup_pack_refs(
    current_message: str | None,
    *,
    client_slug: str | None = None,
) -> list[str] | None:
    expected_pack_refs = _policy_core_current_message_hours_location_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs != ["hours", "location"]:
        return None
    if not _policy_core_current_message_has_booking_side_ask(current_message):
        return None
    return expected_pack_refs


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
    if not _policy_core_current_message_has_temporal_booking_side_ask(current_message):
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
        if _policy_core_current_message_has_master_query_signal(
            current_message,
            client_slug=client_slug,
        ):
            refs.append("master")
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


def _policy_core_current_message_service_multifact_booking_followup_pack_refs(
    current_message: str | None,
    *,
    client_slug: str | None = None,
) -> list[str] | None:
    expected_pack_refs = _policy_core_current_message_service_multifact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return None
    if not _policy_core_current_message_has_temporal_booking_side_ask(current_message):
        return None
    normalized_pack_refs = {
        item.strip().casefold()
        for item in expected_pack_refs
        if isinstance(item, str) and item.strip()
    }
    if "promotions" in normalized_pack_refs:
        return None
    if not normalized_pack_refs.intersection(_SERVICE_QUERY_MULTI_FACT_BOOKING_FOLLOWUP_HEAD_REFS):
        return None
    return expected_pack_refs


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
_SERVICE_QUERY_MULTI_FACT_BOOKING_FOLLOWUP_HEAD_REFS = frozenset(
    {
        "pricing",
        "duration",
        "master",
        "services_overview",
    }
)


def _policy_core_contract_grounded_service(
    contract: LlmPolicyCoreOutput,
) -> str | None:
    slot_service = contract.slots.get("service")
    if isinstance(slot_service, str) and slot_service.strip():
        return " ".join(slot_service.split())
    referent_payload = contract.referents.get("service") if isinstance(contract.referents, Mapping) else None
    if isinstance(referent_payload, Mapping):
        raw_value = referent_payload.get("value")
        if isinstance(raw_value, str) and raw_value.strip():
            return " ".join(raw_value.split())
        raw_entity_id = referent_payload.get("entity_id")
        if isinstance(raw_entity_id, str) and raw_entity_id.strip():
            normalized_entity_id = " ".join(raw_entity_id.split())
            if ":" not in normalized_entity_id:
                return normalized_entity_id
    return None


def _policy_core_contract_has_unsupported_service_availability_grounding_gap(
    contract: LlmPolicyCoreOutput,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if contract.action != "fact" or contract.tool_action_hint != "catalog.service_query":
        return False
    service_pack_refs = set(_policy_core_catalog_service_pack_refs(contract))
    if "services_overview" not in service_pack_refs and contract.intent not in {"services_overview", "out_of_domain"}:
        return False
    grounded_service = _policy_core_resolve_current_message_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    candidate = _policy_core_unsupported_service_availability_candidate(
        current_message,
        grounded_service=grounded_service,
    )
    if not candidate:
        return False
    contract_service = _policy_core_contract_grounded_service(contract)
    if not contract_service:
        return True
    return _normalize_text(contract_service) != _normalize_text(candidate)


def _policy_core_contract_has_unsupported_service_booking_continuation_gap(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    unsupported_service = _policy_core_memory_unsupported_service_fact(normalized_memory_profile)
    if not unsupported_service:
        return False
    current_service_hint = _policy_core_resolve_current_message_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    if current_service_hint:
        return False
    if not _policy_core_current_message_has_booking_desire_signal(
        current_message,
        client_slug=client_slug,
    ):
        return False
    if not (
        _policy_core_current_message_has_message_grounded_temporal_clue(current_message)
        or _policy_core_current_message_has_temporal_booking_side_ask(current_message)
    ):
        return False
    if contract.action != "fact" or contract.tool_action_hint != "catalog.service_query":
        return True
    if "services_overview" not in set(_policy_core_catalog_service_pack_refs(contract)):
        return True
    if any(
        (
            contract.expected_reply_type,
            contract.next_question,
            list(contract.open_questions or []),
            contract.pending_question_act,
            contract.pending_question_target,
            contract.active_question_relation,
        )
    ):
        return True
    contract_service = _policy_core_contract_grounded_service(contract)
    return bool(
        contract_service
        and _normalize_text(contract_service) != _normalize_text(unsupported_service)
    )


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


def _policy_core_memory_unsupported_service_fact(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(normalized_memory_profile, Mapping):
        return None
    semantic_contract = _policy_core_memory_semantic_contract(normalized_memory_profile)
    if _policy_core_payload_token(semantic_contract.get("subject_kind")) != "service":
        return None
    if _policy_core_payload_token(semantic_contract.get("capability")) != "other":
        return None
    if _policy_core_payload_token(semantic_contract.get("resolution_mode")) != "policy_fact":
        return None
    return _policy_core_memory_grounded_service(normalized_memory_profile)


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


def _policy_core_current_message_mentions_grounded_service_value(
    *,
    current_message: str | None,
    grounded_service: str | None,
) -> bool:
    normalized_message = _policy_core_normalize_surface_text(current_message)
    normalized_service = _policy_core_normalize_surface_text(grounded_service)
    if not normalized_message or not normalized_service:
        return False
    return normalized_service.casefold() in normalized_message.casefold()


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
    alternate_datetime = _policy_core_normalize_surface_text(
        semantic_contract.get("alternate_datetime")
    )
    if alternate_datetime:
        return alternate_datetime
    if _policy_core_payload_token(semantic_contract.get("temporal_scope")) != "specific_time":
        return None
    slot_state = (
        normalized_memory_profile.get("slot_state")
        if isinstance(normalized_memory_profile.get("slot_state"), Mapping)
        else None
    )
    if not isinstance(slot_state, Mapping):
        return None
    return _policy_core_normalize_surface_text(slot_state.get("datetime"))


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


def _policy_core_active_booking_info_interrupt_signature(
    contract: LlmPolicyCoreOutput,
) -> dict[str, Any] | None:
    return resolve_policy_core_booking_info_interrupt_signature(
        intent=_policy_core_payload_token(contract.intent),
        capability=_policy_core_payload_token(contract.capability),
        pack_refs=tuple(_policy_core_catalog_service_pack_refs(contract)),
    )


def _policy_core_active_booking_info_interrupt_variant(
    contract: LlmPolicyCoreOutput,
):
    return resolve_policy_core_booking_info_interrupt_variant(
        intent=_policy_core_payload_token(contract.intent),
        capability=_policy_core_payload_token(contract.capability),
        pack_refs=tuple(_policy_core_catalog_service_pack_refs(contract)),
    )


def _policy_core_active_booking_info_interrupt_expected_subject_kind(
    signature: Mapping[str, Any] | None,
    *,
    grounded_service: str | None,
) -> str:
    families = {
        _policy_core_payload_token(item)
        for item in list(signature.get("families") or [])
        if isinstance(signature, Mapping)
    }
    if "service_grounding_progression" in families and isinstance(grounded_service, str) and grounded_service:
        return "service"
    return "general"


def _policy_core_active_booking_info_interrupt_grounding_clause(
    signature: Mapping[str, Any] | None,
    *,
    grounded_service: str | None,
) -> str:
    expected_subject_kind = _policy_core_active_booking_info_interrupt_expected_subject_kind(
        signature,
        grounded_service=grounded_service,
    )
    if expected_subject_kind == "service":
        return _policy_core_grounded_service_repair_clause(grounded_service)
    return (
        "Because this interrupt answers a salon-level fact on the current turn, keep "
        '`subject_kind="general"` and leave `slots.service` / `referents.service` empty '
        "instead of rewriting the fact turn into service-scoped grounding."
    )


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
    slot_name = _policy_core_payload_token(contract.slots.get("name"))
    if isinstance(slot_name, str) and slot_name.strip():
        return slot_name.strip()
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
    has_contact = bool(
        contract.slots.get("phone")
        or contract.slots.get("contact")
        or _policy_core_memory_slot_value(normalized_memory_profile, "phone")
        or _policy_core_memory_slot_value(normalized_memory_profile, "contact")
    )
    return bool(grounded_service and has_datetime and has_customer and has_contact)


def _policy_core_calendar_book_slot_commit_contract_ready(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if contract.intent != "booking":
        return False
    if contract.action != "fact":
        return False
    if contract.tool_action_hint != "calendar.book_slot":
        return False
    if contract.subject_kind != "booking":
        return False
    if contract.capability != "bookability":
        return False
    if contract.resolution_mode != "live_calendar":
        return False
    if not _policy_core_booking_commit_ready(contract, normalized_memory_profile):
        return False
    contract_datetime = _policy_core_payload_token(contract.slots.get("datetime"))
    if not contract_datetime:
        return False
    if not _policy_core_booking_datetime_surface_is_executable(contract_datetime):
        return False
    if contract.temporal_scope != "specific_time":
        return False
    if contract.expected_reply_type is not None:
        return False
    if contract.next_question is not None:
        return False
    if list(contract.open_questions or []) != []:
        return False
    if any(
        (
            contract.pending_question_act,
            contract.pending_question_target,
            contract.active_question_relation,
        )
    ):
        return False
    return True


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
        contract.action == "handoff"
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
        raw_terms: list[str] = []
        raw_label = raw_card.get("label")
        canonical_match_value = (
            " ".join(raw_label.split())
            if raw_card.get("kind") == "service_catalog"
            and isinstance(raw_label, str)
            and raw_label.strip()
            else None
        )
        if isinstance(raw_label, str) and raw_label.strip():
            raw_terms.append(raw_label)
            raw_terms.extend(
                part
                for part in _POLICY_CORE_SERVICE_CARD_LABEL_SPLIT_PATTERN.split(raw_label)
                if isinstance(part, str) and part.strip()
            )
        for key in ("includes", "synonyms"):
            raw_values = raw_card.get(key)
            if not isinstance(raw_values, list):
                continue
            raw_terms.extend(
                item for item in raw_values if isinstance(item, str) and item.strip()
            )
        for raw_term in raw_terms:
            normalized_term = _normalize_text(raw_term)
            if not normalized_term or not _policy_core_service_phrase_matches_message(
                normalized_term,
                normalized_message=normalized_message,
                padded_message=padded_message,
            ):
                continue
            match_value = canonical_match_value or " ".join(raw_term.split())
            fingerprint = match_value.casefold()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            matches.append((len(normalized_term), match_value))
    if not matches:
        return None
    matches.sort(key=lambda item: (-item[0], item[1]))
    return matches[0][1]


def _policy_core_context_service_matches(
    message: str | None,
    context_payload: Mapping[str, Any] | None,
    *,
    client_slug: str | None = None,
) -> list[str]:
    if not isinstance(message, str) or not message.strip():
        return []
    if not isinstance(context_payload, Mapping):
        return []
    raw_cards = context_payload.get("service_cards")
    if not isinstance(raw_cards, list):
        return []
    normalized_message = _normalize_text(message)
    if not normalized_message:
        return []
    padded_message = f" {normalized_message} "
    matches: list[tuple[int, str]] = []
    seen: set[str] = set()
    for raw_card in raw_cards:
        if not isinstance(raw_card, Mapping):
            continue
        raw_terms: list[str] = []
        raw_label = raw_card.get("label")
        canonical_match_value = (
            " ".join(raw_label.split())
            if raw_card.get("kind") == "service_catalog"
            and isinstance(raw_label, str)
            and raw_label.strip()
            else None
        )
        if isinstance(raw_label, str) and raw_label.strip():
            raw_terms.append(raw_label)
            raw_terms.extend(
                part
                for part in _POLICY_CORE_SERVICE_CARD_LABEL_SPLIT_PATTERN.split(raw_label)
                if isinstance(part, str) and part.strip()
            )
        for key in ("includes", "synonyms"):
            raw_values = raw_card.get(key)
            if isinstance(raw_values, list):
                raw_terms.extend(
                    item for item in raw_values if isinstance(item, str) and item.strip()
                )
        for raw_term in raw_terms:
            normalized_term = _normalize_text(raw_term)
            if not normalized_term:
                continue
            if not _policy_core_service_phrase_matches_message(
                normalized_term,
                normalized_message=normalized_message,
                padded_message=padded_message,
            ):
                continue
            match_value = canonical_match_value or " ".join(raw_term.split())
            fingerprint = match_value.casefold()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            matches.append((len(normalized_term), match_value))
    matches.sort(key=lambda item: (-item[0], item[1]))
    return [match for _, match in matches]


def _policy_core_pack_runtime_service_hint(
    message: str | None,
    *,
    client_slug: str | None,
) -> str | None:
    normalized_message = _normalize_text(message)
    if not normalized_message:
        return None
    if not isinstance(client_slug, str) or not client_slug.strip():
        return None
    try:
        from app.services.pack_runtime_service import get_pack_runtime

        pack_runtime = get_pack_runtime(client_slug)
        match = pack_runtime.match_service(normalized_message)
    except Exception:
        return None
    if not isinstance(match, Mapping):
        return None
    raw_name = match.get("name")
    if isinstance(raw_name, str) and raw_name.strip():
        return " ".join(raw_name.split())
    return None


def _policy_core_pack_runtime_service_matches(
    message: str | None,
    *,
    client_slug: str | None,
) -> list[str]:
    normalized_message = _normalize_text(message)
    if not normalized_message:
        return []
    if not isinstance(client_slug, str) or not client_slug.strip():
        return []
    try:
        from app.services.pack_runtime_service import load_yaml_truth

        truth = load_yaml_truth(client_slug)
    except Exception:
        return []
    if not isinstance(truth, Mapping):
        return []
    raw_catalog = truth.get("services_catalog")
    services = []
    if isinstance(raw_catalog, Mapping):
        raw_services = raw_catalog.get("services") or raw_catalog.get("items")
        if isinstance(raw_services, list):
            services = [item for item in raw_services if isinstance(item, Mapping)]
    elif isinstance(raw_catalog, list):
        services = [item for item in raw_catalog if isinstance(item, Mapping)]
    padded_message = f" {normalized_message} "
    matches: list[tuple[int, str]] = []
    seen: set[str] = set()
    for service_item in services:
        raw_name = service_item.get("name")
        canonical_name = " ".join(raw_name.split()) if isinstance(raw_name, str) and raw_name.strip() else None
        raw_terms: list[str] = []
        if canonical_name:
            raw_terms.append(canonical_name)
        for key in ("aliases", "price_items"):
            raw_values = service_item.get(key)
            if isinstance(raw_values, list):
                raw_terms.extend(
                    item for item in raw_values if isinstance(item, str) and item.strip()
                )
        for raw_term in raw_terms:
            normalized_term = _normalize_text(raw_term)
            if not normalized_term:
                continue
            if not _policy_core_service_phrase_matches_message(
                normalized_term,
                normalized_message=normalized_message,
                padded_message=padded_message,
            ):
                continue
            match_value = canonical_name or " ".join(raw_term.split())
            fingerprint = match_value.casefold()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            matches.append((len(normalized_term), match_value))
    matches.sort(key=lambda item: (-item[0], item[1]))
    return [match for _, match in matches]


def _policy_core_multiple_service_booking_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    service_matches: list[str],
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile):
        return None
    normalized_matches = list(
        dict.fromkeys(
            " ".join(item.split()).casefold()
            for item in service_matches
            if isinstance(item, str) and item.strip()
        )
    )
    normalized_matches = [
        item
        for item in normalized_matches
        if not any(
            item != other and f" {item} " in f" {other} "
            for other in normalized_matches
        )
    ]
    if len(normalized_matches) < 2:
        return None
    if not _policy_core_current_message_has_booking_desire_signal(
        current_message,
        client_slug=client_slug,
    ):
        return None
    service_value = " и ".join(normalized_matches[:3])
    temporal_surface = _policy_core_current_message_temporal_clue_surface(current_message)
    slots: dict[str, Any] = {"service": service_value}
    if temporal_surface:
        slots["datetime"] = temporal_surface
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "slots": slots,
        "expected_reply_type": "service_choice",
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "goal": "booking",
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": (
            _policy_core_current_message_grounded_temporal_scope_hint(current_message)
            or "none"
        ),
        "alternate_datetime": temporal_surface,
        "resolution_mode": "clarify_missing_subject",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "reason": "multiple_services_require_single_service_choice",
        "referents": {
            "service": _policy_core_service_referent(
                service_value,
                source_ref="message_grounding",
            )
        },
    }


def _policy_core_resolve_current_message_service_hint(
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> str | None:
    if isinstance(context_payload, Mapping):
        raw_hints = context_payload.get("message_grounding_hints")
        if isinstance(raw_hints, Mapping):
            raw_service = raw_hints.get("service")
            if isinstance(raw_service, str):
                normalized_service = " ".join(raw_service.split())
                if normalized_service:
                    return normalized_service

    grounded_service_hint = _policy_core_context_service_hint(
        current_message,
        context_payload,
        client_slug=client_slug,
    )
    if grounded_service_hint:
        return grounded_service_hint

    if isinstance(client_slug, str) and client_slug.strip():
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
        if grounded_service_hint:
            return grounded_service_hint
    pack_matches = _policy_core_pack_runtime_service_matches(
        current_message,
        client_slug=client_slug,
    )
    if pack_matches:
        return pack_matches[0]
    return _policy_core_pack_runtime_service_hint(current_message, client_slug=client_slug)


def _policy_core_resolve_standalone_service_fact_variant(
    current_message: str | None,
    *,
    client_slug: str | None,
) -> PolicyCoreBookingInfoInterruptVariantV1 | None:
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return None
    if _policy_core_current_message_has_booking_desire_signal(
        current_message,
        client_slug=client_slug,
    ):
        return None
    if _policy_core_current_message_has_booking_or_location_side_ask(current_message):
        return None
    if _policy_core_current_message_hours_service_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    ) is not None:
        return None
    if _policy_core_current_message_service_multifact_pack_refs(
        current_message,
        client_slug=client_slug,
    ) is not None:
        return None
    if _policy_core_current_message_has_promotions_query(current_message):
        return resolve_policy_core_booking_info_interrupt_variant(
            intent="promotions",
            capability="promotions",
            pack_refs=("promotions",),
        )
    from app.services.pack_runtime_service import get_pack_runtime

    try:
        pack_runtime = get_pack_runtime(client_slug)
    except Exception:
        pack_runtime = None
    if pack_runtime is not None:
        try:
            if pack_runtime.has_duration_signal(
                normalized_message,
                message=current_message,
            ):
                return resolve_policy_core_booking_info_interrupt_variant(
                    intent="duration",
                    capability="duration",
                    pack_refs=("duration",),
                )
        except Exception:
            pass
        try:
            if pack_runtime.has_price_signal(
                normalized_message,
                message=current_message,
            ):
                return resolve_policy_core_booking_info_interrupt_variant(
                    intent="pricing",
                    capability="pricing",
                    pack_refs=("pricing",),
                )
        except Exception:
            pass
    if _policy_core_current_message_has_master_query_signal(
        current_message,
        client_slug=client_slug,
    ):
        return resolve_policy_core_booking_info_interrupt_variant(
            intent="master_query",
            capability="master",
            pack_refs=("master",),
        )
    return None


def _policy_core_standalone_service_fact_forced_fields(
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    grounded_service: str | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(
        normalized_memory_profile
    ) or _policy_core_resume_pending_contract(normalized_memory_profile):
        return None
    if not isinstance(grounded_service, str) or not grounded_service.strip():
        return None
    variant = _policy_core_resolve_standalone_service_fact_variant(
        current_message,
        client_slug=client_slug,
    )
    if variant is None:
        return None
    service_value = " ".join(grounded_service.split())
    return {
        "intent": variant.head_intent,
        "action": "fact",
        "tool_action_hint": variant.tool_action_hint,
        "pack_refs": list(variant.pack_refs),
        "slots": {"service": service_value},
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "subject_kind": "service",
        "capability": variant.capability,
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "referents": {
            "service": {
                "value": service_value,
                "entity_id": None,
                "entity_type": "service",
                "source_ref": "message_grounding",
            }
        },
        "reason": "standalone_service_fact_grounded_from_catalog_alias",
    }


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
    return _policy_core_resolve_current_message_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)


def _policy_core_payload_reason_or_default(
    payload: Mapping[str, Any] | None,
    *,
    default: str,
) -> str:
    if isinstance(payload, Mapping):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            return " ".join(raw_reason.split())
    return default


def _policy_core_render_generated_contract_boundary_payload(
    template_id: str,
    *,
    payload: Mapping[str, Any] | None,
    reason: str,
    **values: Any,
) -> dict[str, Any]:
    language = payload.get("language") if isinstance(payload, Mapping) else None
    confidence = payload.get("confidence") if isinstance(payload, Mapping) else None
    return render_policy_core_generated_contract_boundary_payload_template(
        template_id,
        language=language,
        confidence=confidence,
        reason=reason,
        **values,
    )


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
    if "service" not in normalized_referents:
        normalized_referents["service"] = {
            "value": effective_service,
            "entity_type": "service",
            "source_ref": "carryover",
        }
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_location_head_intent_with_service_fact_requests",
    )
    if _policy_core_current_message_has_temporal_booking_side_ask(current_message):
        pending_question_act = _policy_core_payload_token(
            payload.get("pending_question_act") if isinstance(payload, Mapping) else None
        )
        if pending_question_act not in {"ask_about_requested_slot", "slot_constraint"}:
            pending_question_act = (
                "slot_constraint"
                if _policy_core_current_message_has_message_grounded_temporal_clue(current_message)
                else "ask_about_requested_slot"
            )
        temporal_scope = (
            _policy_core_payload_token(payload.get("temporal_scope"))
            if isinstance(payload, Mapping)
            else None
        )
        alternate_datetime = _policy_core_normalize_surface_text(
            payload.get("alternate_datetime") if isinstance(payload, Mapping) else None
        )
        if alternate_datetime is not None and _policy_core_temporal_clue_requires_message_grounded_alternate_datetime(
            alternate_datetime,
            current_message,
        ):
            alternate_datetime = None
        if not alternate_datetime:
            temporal_scope = "none"
        elif temporal_scope in {None, "none"}:
            temporal_scope = _policy_core_current_message_grounded_temporal_scope_hint(current_message) or "none"
        return _policy_core_render_generated_contract_boundary_payload(
            "mixed_first_turn_location_service_fact_booking_followup_boundary",
            payload=payload,
            reason=reason,
            pack_refs=list(expected_pack_refs),
            slots=normalized_slots,
            referents=normalized_referents,
            temporal_scope=temporal_scope or "none",
            alternate_datetime=alternate_datetime,
            pending_question_act=pending_question_act,
        )
    return _policy_core_render_generated_contract_boundary_payload(
        "mixed_first_turn_location_service_fact_scope_boundary",
        payload=payload,
        reason=reason,
        pack_refs=list(expected_pack_refs),
        slots=normalized_slots,
        referents=normalized_referents,
    )


def _policy_core_build_mixed_first_turn_hours_location_booking_followup_boundary_payload(
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
    expected_pack_refs = _policy_core_current_message_hours_location_booking_followup_pack_refs(
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
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_hours_location_head_with_missing_service_booking_request",
    )
    return _policy_core_render_generated_contract_boundary_payload(
        "mixed_first_turn_hours_location_booking_followup_boundary",
        payload=payload,
        reason=reason,
        head_ref=head_ref,
        pack_refs=list(expected_pack_refs),
    )


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
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_hours_location_fact_request",
    )
    return _policy_core_render_generated_contract_boundary_payload(
        "mixed_first_turn_hours_location_fact_scope_boundary",
        payload=payload,
        reason=reason,
        head_ref=head_ref,
        pack_refs=list(expected_pack_refs),
    )


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
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_hours_head_intent_with_service_fact_requests",
    )
    return _policy_core_render_generated_contract_boundary_payload(
        "mixed_first_turn_hours_service_fact_scope_boundary",
        payload=payload,
        reason=reason,
        pack_refs=list(expected_pack_refs),
        slots=normalized_slots,
        referents=normalized_referents,
    )


def _policy_core_build_mixed_first_turn_hours_service_booking_followup_boundary_payload(
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
    expected_pack_refs = _policy_core_current_message_hours_service_booking_followup_pack_refs(
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
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_hours_head_service_fact_with_booking_followup",
    )
    return _policy_core_render_generated_contract_boundary_payload(
        "mixed_first_turn_hours_service_booking_followup_boundary",
        payload=payload,
        reason=reason,
        pack_refs=list(expected_pack_refs),
        slots={"service": effective_service},
        referents=normalized_referents,
    )


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
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_hours_location_head_intent_with_service_fact_requests",
    )
    return _policy_core_render_generated_contract_boundary_payload(
        "mixed_first_turn_hours_location_service_fact_scope_boundary",
        payload=payload,
        reason=reason,
        head_ref=head_ref,
        pack_refs=list(expected_pack_refs),
        slots=normalized_slots,
        referents=normalized_referents,
    )


def _policy_core_apply_prevalidate_boundary_normalizations(
    *,
    payload: dict[str, Any],
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> tuple[dict[str, Any], str | None]:
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
        return (
            normalized_promotions_location_booking_payload,
            "promotions_location_booking_followup_boundary",
        )
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
        return (
            normalized_promotions_grounded_booking_payload,
            "promotions_grounded_service_booking_followup_boundary",
        )
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
        return (
            normalized_promotions_booking_payload,
            "promotions_booking_followup_boundary",
        )
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
        return (
            normalized_hours_location_service_payload,
            "mixed_first_turn_hours_location_service_fact_scope_boundary",
        )
    normalized_hours_service_payload = _policy_core_build_mixed_first_turn_hours_service_fact_boundary_payload(
        payload=payload,
        normalized_memory_profile=normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    if normalized_hours_service_payload is not None:
        return (
            normalized_hours_service_payload,
            "mixed_first_turn_hours_service_fact_scope_boundary",
        )
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
        return (
            normalized_service_fact_side_booking_payload,
            "mixed_first_turn_service_fact_booking_side_precedence_boundary",
        )
    return payload, None


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
    if "service" not in normalized_referents:
        normalized_referents["service"] = {
            "value": effective_service,
            "entity_type": "service",
            "source_ref": "carryover",
        }
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_service_fact_head_intent_with_side_booking_request",
    )
    pending_question_act = _policy_core_payload_token(
        payload.get("pending_question_act") if isinstance(payload, Mapping) else None
    )
    if pending_question_act not in {"ask_about_requested_slot", "slot_constraint"}:
        pending_question_act = (
            "slot_constraint"
            if _policy_core_current_message_has_message_grounded_temporal_clue(current_message)
            else "ask_about_requested_slot"
        )
    temporal_scope = _policy_core_payload_token(payload.get("temporal_scope")) if isinstance(payload, Mapping) else None
    alternate_datetime = _policy_core_normalize_surface_text(
        payload.get("alternate_datetime") if isinstance(payload, Mapping) else None
    )
    if alternate_datetime is not None and _policy_core_temporal_clue_requires_message_grounded_alternate_datetime(
        alternate_datetime,
        current_message,
    ):
        alternate_datetime = None
    if not alternate_datetime:
        temporal_scope = "none"
    elif temporal_scope in {None, "none"}:
        temporal_scope = _policy_core_current_message_grounded_temporal_scope_hint(current_message) or "none"
    return _policy_core_render_generated_contract_boundary_payload(
        "mixed_first_turn_service_fact_booking_side_precedence_boundary",
        payload=payload,
        reason=reason,
        expected_ref=expected_ref,
        pack_refs=[expected_ref],
        slots=normalized_slots,
        referents=normalized_referents,
        temporal_scope=temporal_scope or "none",
        alternate_datetime=alternate_datetime,
        pending_question_act=pending_question_act,
    )


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
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_same_service_multifact_fact_request",
    )
    return _policy_core_render_generated_contract_boundary_payload(
        "service_query_multifact_scope_boundary",
        payload=payload,
        reason=reason,
        head_intent=head_intent,
        head_ref=head_ref,
        pack_refs=list(expected_pack_refs),
        slots=normalized_slots,
        referents=normalized_referents,
    )


def _policy_core_build_service_query_multifact_booking_followup_boundary_payload(
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
    expected_pack_refs = _policy_core_current_message_service_multifact_booking_followup_pack_refs(
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
    if "service" not in normalized_referents:
        normalized_referents["service"] = {
            "value": effective_service,
            "entity_type": "service",
            "source_ref": "carryover",
        }
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_same_service_multifact_fact_with_booking_followup",
    )
    pending_question_act = _policy_core_payload_token(
        payload.get("pending_question_act") if isinstance(payload, Mapping) else None
    )
    if pending_question_act not in {"ask_about_requested_slot", "slot_constraint"}:
        pending_question_act = (
            "slot_constraint"
            if _policy_core_current_message_has_message_grounded_temporal_clue(current_message)
            else "ask_about_requested_slot"
        )
    temporal_scope = _policy_core_payload_token(payload.get("temporal_scope")) if isinstance(payload, Mapping) else None
    alternate_datetime = _policy_core_normalize_surface_text(
        payload.get("alternate_datetime") if isinstance(payload, Mapping) else None
    )
    if alternate_datetime is not None and _policy_core_temporal_clue_requires_message_grounded_alternate_datetime(
        alternate_datetime,
        current_message,
    ):
        alternate_datetime = None
    if not alternate_datetime:
        temporal_scope = "none"
    elif temporal_scope in {None, "none"}:
        temporal_scope = _policy_core_current_message_grounded_temporal_scope_hint(current_message) or "none"
    return _policy_core_render_generated_contract_boundary_payload(
        "service_query_multifact_booking_followup_boundary",
        payload=payload,
        reason=reason,
        head_intent=head_intent,
        head_ref=head_ref,
        pack_refs=list(expected_pack_refs),
        slots=normalized_slots,
        referents=normalized_referents,
        temporal_scope=temporal_scope or "none",
        alternate_datetime=alternate_datetime,
        pending_question_act=pending_question_act,
    )


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


def _policy_core_build_booking_availability_missing_service_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if not isinstance(current_message, str) or not current_message.strip():
        return None
    normalized_message = " ".join(current_message.split())
    if not _policy_core_current_message_has_message_grounded_temporal_clue(normalized_message):
        return None
    if not any(
        pattern.search(normalized_message)
        for pattern in _POLICY_CORE_GENERIC_AVAILABILITY_QUERY_PATTERNS
    ):
        return None
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=normalized_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service_hint:
        return None
    temporal_scope = (
        _policy_core_current_message_grounded_temporal_scope_hint(normalized_message)
        or _policy_core_payload_token(payload.get("temporal_scope") if isinstance(payload, Mapping) else None)
        or "day"
    )
    exact_datetime = _policy_core_current_message_exact_datetime_surface(normalized_message)
    alternate_datetime = exact_datetime
    if not alternate_datetime and isinstance(payload, Mapping):
        payload_alternate_datetime = payload.get("alternate_datetime")
        if isinstance(payload_alternate_datetime, str) and payload_alternate_datetime.strip():
            alternate_datetime = " ".join(payload_alternate_datetime.split())
    if not alternate_datetime:
        alternate_datetime = normalized_message.strip(" ,.!?:") or None
    normalized_slots: dict[str, Any] = {}
    if temporal_scope == "specific_time" and alternate_datetime:
        normalized_slots["datetime"] = alternate_datetime
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "slots": normalized_slots,
        "expected_reply_type": "service_choice",
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": "booking_availability_missing_service_boundary",
        "goal": "booking",
        "entity_refs": [],
        "referents": {},
        "subject_kind": "general",
        "capability": "bookability",
        "temporal_scope": temporal_scope,
        "alternate_datetime": alternate_datetime,
        "resolution_mode": "clarify_missing_subject",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_build_mixed_first_turn_promotions_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None = None,
    client_slug: str | None = None,
) -> dict[str, Any] | None:
    del context_payload, client_slug
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
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_promotions_head_intent_with_side_requests",
    )
    return _policy_core_render_generated_contract_boundary_payload(
        "mixed_first_turn_promotions_precedence_fact_scope_boundary",
        payload=payload,
        reason=reason,
        pack_refs=list(expected_pack_refs),
        slots=normalized_slots,
        referents=normalized_referents,
        subject_kind="service" if grounded_service else "general",
    )


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
    reason = _policy_core_payload_reason_or_default(
        payload,
        default="standalone_promotions_head_with_missing_service_booking_request",
    )
    return _policy_core_render_generated_contract_boundary_payload(
        "promotions_booking_followup_boundary",
        payload=payload,
        reason=reason,
        pack_refs=list(expected_pack_refs),
    )


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
    if expected_pack_refs is None or not _policy_core_current_message_has_temporal_booking_side_ask(current_message):
        return None
    grounded_service = _policy_core_payload_grounded_service(payload) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service:
        return None
    return _policy_core_render_generated_contract_boundary_payload(
        "promotions_location_booking_followup_boundary",
        payload=payload,
        reason=_policy_core_payload_reason_or_default(
            payload,
            default="standalone_promotions_location_head_with_missing_service_booking_request",
        ),
        pack_refs=list(expected_pack_refs),
    )


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
    return _policy_core_render_generated_contract_boundary_payload(
        "promotions_grounded_service_booking_followup_boundary",
        payload=payload,
        reason=_policy_core_payload_reason_or_default(
            payload,
            default="standalone_promotions_head_with_grounded_service_booking_request",
        ),
        pack_refs=list(expected_pack_refs),
        slots={"service": grounded_service},
        referents=normalized_referents,
    )


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
    carried_temporal_scope = _policy_core_memory_temporal_scope(normalized_memory_profile)
    if (
        isinstance(carried_temporal_scope, str)
        and carried_temporal_scope
        and _policy_core_payload_token(contract.temporal_scope) != carried_temporal_scope
    ):
        return True
    carried_alternate_datetime = _policy_core_memory_alternate_datetime(
        normalized_memory_profile
    )
    contract_alternate_datetime = _policy_core_normalize_surface_text(
        contract.alternate_datetime
    )
    if isinstance(carried_alternate_datetime, str) and carried_alternate_datetime:
        contract_signature = (
            contract_alternate_datetime.casefold()
            if isinstance(contract_alternate_datetime, str)
            else None
        )
        if contract_signature != carried_alternate_datetime.casefold():
            return True
    return False


def _policy_core_is_active_booking_info_interrupt_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if _policy_core_has_active_media_resume(normalized_memory_profile):
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    signature = _policy_core_active_booking_info_interrupt_signature(contract)
    if signature is None:
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    expected_reply_type = carry_contract.get("expected_reply_type")
    expected_next_question = carry_contract.get("next_question")
    if contract.action != "fact":
        return True
    if _policy_core_payload_token(contract.goal) != "booking":
        return True
    if contract.intent != signature["head_intent"]:
        return True
    if contract.tool_action_hint != signature["tool_action_hint"]:
        return True
    if _policy_core_catalog_service_pack_refs(contract) != signature["pack_refs"]:
        return True
    expected_subject_kind = (
        "general" if signature["tool_action_hint"] == "catalog.location" else "service"
    )
    if contract.subject_kind != expected_subject_kind:
        return True
    if contract.capability != signature["capability"]:
        return True
    if contract.resolution_mode != "policy_fact":
        return True
    if isinstance(expected_reply_type, str) and expected_reply_type.strip():
        if contract.expected_reply_type != expected_reply_type:
            return True
    if isinstance(expected_next_question, str) and expected_next_question.strip():
        if contract.next_question != expected_next_question:
            return True
        if list(contract.open_questions or []) != _policy_core_expected_open_questions(
            carry_contract
        ):
            return True
    pending_act = carry_contract.get("pending_question_act")
    if isinstance(pending_act, str) and pending_act.strip():
        if contract.pending_question_act != pending_act:
            return True
    pending_target = carry_contract.get("pending_question_target")
    if isinstance(pending_target, str) and pending_target.strip():
        if contract.pending_question_target != pending_target:
            return True
    if contract.active_question_relation != "generic_info_interrupt":
        return True
    carried_temporal_scope = _policy_core_memory_temporal_scope(normalized_memory_profile)
    if (
        isinstance(carried_temporal_scope, str)
        and carried_temporal_scope
        and _policy_core_payload_token(contract.temporal_scope) != carried_temporal_scope
    ):
        return True
    carried_alternate_datetime = _policy_core_memory_alternate_datetime(
        normalized_memory_profile
    )
    contract_alternate_datetime = _policy_core_normalize_surface_text(
        contract.alternate_datetime
    )
    if isinstance(carried_alternate_datetime, str) and carried_alternate_datetime:
        contract_signature = (
            contract_alternate_datetime.casefold()
            if isinstance(contract_alternate_datetime, str)
            else None
        )
        if contract_signature != carried_alternate_datetime.casefold():
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
    grounded_service_hint = _policy_core_resolve_current_message_service_hint(
        current_message=normalized_message,
        context_payload=context_payload,
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


def _policy_core_has_missing_service_exact_datetime_service_choice_context(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if _policy_core_payload_token(carry_contract.get("expected_reply_type")) != "service_choice":
        return False
    if _policy_core_payload_token(carry_contract.get("next_question")) != "service":
        return False
    open_questions = _policy_core_expected_open_questions(carry_contract)
    if open_questions != ["service"]:
        return False
    if _policy_core_memory_temporal_scope(normalized_memory_profile) != "specific_time":
        return False
    if not _policy_core_memory_alternate_datetime(normalized_memory_profile):
        return False
    return True


def _policy_core_is_missing_service_exact_datetime_grounded_fact_interrupt_progression_context(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if not _policy_core_has_missing_service_exact_datetime_service_choice_context(
        normalized_memory_profile
    ):
        return False
    variant = _policy_core_active_booking_info_interrupt_variant(contract)
    if variant is None or "service_grounding_progression" not in variant.families:
        return False
    if _policy_core_active_booking_info_interrupt_signature(contract) is None:
        return False
    grounded_service = _policy_core_resolve_current_message_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    if grounded_service:
        return True
    contract_grounded_service = _policy_core_contract_grounded_service(contract)
    return _policy_core_current_message_mentions_grounded_service_value(
        current_message=current_message,
        grounded_service=contract_grounded_service,
    )


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
    if expected_pack_refs is None or not _policy_core_current_message_has_temporal_booking_side_ask(current_message):
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
    if expected_pack_refs is None or not _policy_core_current_message_has_temporal_booking_side_ask(current_message):
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


def _policy_core_is_canonical_mixed_first_turn_hours_service_booking_followup_contract(
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
    expected_pack_refs = _policy_core_current_message_hours_service_booking_followup_pack_refs(
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
    if not grounded_service:
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
    if normalized_pack_refs != {
        item.strip().casefold()
        for item in expected_pack_refs
        if isinstance(item, str) and item.strip()
    }:
        return False
    if contract.intent != "hours":
        return False
    if contract.subject_kind != "service":
        return False
    if contract.capability != "hours":
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if _policy_core_payload_token(contract.goal) != "booking":
        return False
    if contract.expected_reply_type != "time":
        return False
    if contract.next_question != "datetime":
        return False
    if list(contract.open_questions or []) != ["datetime"]:
        return False
    if contract.pending_question_target != "time":
        return False
    if contract.pending_question_act not in {"ask_about_requested_slot", "slot_constraint"}:
        return False
    return contract.active_question_relation == contract.pending_question_act


def _policy_core_is_mixed_first_turn_hours_service_booking_followup_contract(
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
    expected_pack_refs = _policy_core_current_message_hours_service_booking_followup_pack_refs(
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
    return not _policy_core_is_canonical_mixed_first_turn_hours_service_booking_followup_contract(
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
    if _policy_core_is_canonical_mixed_first_turn_hours_service_booking_followup_contract(
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
    if _policy_core_current_message_hours_location_booking_followup_pack_refs(
        current_message,
        client_slug=client_slug,
    ) is not None:
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


def _policy_core_is_canonical_hours_location_booking_followup_contract(
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
    expected_pack_refs = _policy_core_current_message_hours_location_booking_followup_pack_refs(
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
    open_questions = [
        item.strip().casefold()
        for item in list(contract.open_questions or [])
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
    if contract.subject_kind not in {None, "general"}:
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if _policy_core_payload_token(contract.goal) != "booking":
        return False
    if contract.expected_reply_type != "service_choice":
        return False
    if contract.next_question != "service":
        return False
    if open_questions != ["service"]:
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
    if _policy_core_is_canonical_hours_location_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
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
    if _policy_core_is_canonical_mixed_first_turn_location_service_booking_followup_contract(
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


def _policy_core_is_canonical_mixed_first_turn_location_service_booking_followup_contract(
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
    expected_pack_refs = _policy_core_current_message_location_service_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None or not _policy_core_current_message_has_temporal_booking_side_ask(current_message):
        return False
    grounded_service = _policy_core_contract_grounded_service(contract) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if not grounded_service:
        return False
    normalized_pack_refs = [
        item.strip().casefold()
        for item in list(contract.pack_refs or [])
        if isinstance(item, str) and item.strip()
    ]
    open_questions = {
        item.strip().casefold()
        for item in list(contract.open_questions or [])
        if isinstance(item, str) and item.strip()
    }
    if contract.action != "fact":
        return False
    if contract.tool_action_hint != "info":
        return False
    if normalized_pack_refs != list(expected_pack_refs):
        return False
    if contract.intent != "location":
        return False
    if contract.subject_kind != "service":
        return False
    if contract.capability != "location":
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if _policy_core_payload_token(contract.goal) != "booking":
        return False
    if contract.expected_reply_type != "time":
        return False
    if contract.next_question != "datetime" or "datetime" not in open_questions:
        return False
    pending_question_act = _policy_core_payload_token(contract.pending_question_act)
    if pending_question_act not in {"ask_about_requested_slot", "slot_constraint"}:
        return False
    if _policy_core_payload_token(contract.pending_question_target) != "time":
        return False
    if _policy_core_payload_token(contract.active_question_relation) != pending_question_act:
        return False
    return True


def _policy_core_is_mixed_first_turn_service_fact_booking_side_precedence_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_is_canonical_mixed_first_turn_service_fact_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return False
    if _policy_core_is_canonical_mixed_first_turn_hours_service_booking_followup_contract(
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
    expected_pack_refs = _policy_core_current_message_service_scoped_fact_pack_refs(
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
    return True


def _policy_core_is_canonical_mixed_first_turn_service_fact_booking_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_is_canonical_mixed_first_turn_hours_service_booking_followup_contract(
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
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if _policy_core_payload_token(contract.goal) != "booking":
        return False
    if contract.expected_reply_type != "time":
        return False
    if contract.next_question != "datetime":
        return False
    if list(contract.open_questions or []) != ["datetime"]:
        return False
    if contract.pending_question_target != "time":
        return False
    if contract.pending_question_act not in {"ask_about_requested_slot", "slot_constraint"}:
        return False
    return (
        grounded_service is not None
        and contract.active_question_relation == contract.pending_question_act
    )


def _policy_core_is_canonical_service_query_multifact_booking_followup_contract(
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
    expected_pack_refs = _policy_core_current_message_service_multifact_booking_followup_pack_refs(
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
    if not grounded_service:
        return False
    normalized_pack_refs = _policy_core_catalog_service_pack_refs(contract)
    if contract.action != "fact":
        return False
    if contract.tool_action_hint != "catalog.service_query":
        return False
    if normalized_pack_refs != expected_pack_refs:
        return False
    contract_intent_ref = "master" if contract.intent == "master_query" else contract.intent
    if contract_intent_ref not in expected_pack_refs:
        return False
    if contract.subject_kind != "service":
        return False
    if contract.capability not in expected_pack_refs:
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if _policy_core_payload_token(contract.goal) != "booking":
        return False
    if contract.expected_reply_type != "time":
        return False
    if contract.next_question != "datetime":
        return False
    if list(contract.open_questions or []) != ["datetime"]:
        return False
    if contract.pending_question_target != "time":
        return False
    if contract.pending_question_act not in {"ask_about_requested_slot", "slot_constraint"}:
        return False
    return contract.active_question_relation == contract.pending_question_act


def _policy_core_is_service_query_multifact_booking_followup_contract(
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
    expected_pack_refs = _policy_core_current_message_service_multifact_booking_followup_pack_refs(
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
    return not _policy_core_is_canonical_service_query_multifact_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )


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
    if _policy_core_is_canonical_service_query_multifact_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
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
    if contract.expected_reply_type == "service_choice":
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    if _policy_core_is_booking_service_choice_followup_contract(
        carry_contract,
        normalized_memory_profile,
    ):
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
    if not _policy_core_booking_datetime_surface_is_executable(contract_datetime):
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
    contract_alternate_datetime = _policy_core_normalize_surface_text(
        contract.alternate_datetime
    )
    if not contract_alternate_datetime:
        return True
    if contract_alternate_datetime.casefold() != contract_datetime.casefold():
        return True
    if not _policy_core_booking_datetime_surface_is_executable(contract_alternate_datetime):
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
    if _policy_core_current_message_has_specialist_relaxation_signal(
        current_message,
        client_slug=None,
    ):
        expected_reply_type = carry_contract.get("expected_reply_type")
        expected_next_question = carry_contract.get("next_question")
        if (
            contract.expected_reply_type == expected_reply_type
            and contract.next_question == expected_next_question
            and list(contract.open_questions or [])
            == _policy_core_expected_open_questions(carry_contract)
            and contract.subject_kind == "booking"
            and contract.capability == "bookability"
            and contract.resolution_mode == "direct"
            and contract.pending_question_target == "time"
            and contract.active_question_relation == "fill_requested_slot"
        ):
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
    if contract.subject_kind != "booking":
        return True
    if contract.capability != "bookability":
        return True
    if contract.resolution_mode != "direct":
        return True
    contract_datetime = _policy_core_normalize_surface_text(contract.slots.get("datetime"))
    if not contract_datetime or not _policy_core_current_message_has_explicit_clock_time(
        contract_datetime
    ):
        return True
    contract_alternate_datetime = _policy_core_normalize_surface_text(
        contract.alternate_datetime
    )
    if not contract_alternate_datetime:
        return True
    if contract_alternate_datetime.casefold() != contract_datetime.casefold():
        return True
    if not _policy_core_booking_datetime_surface_is_executable(contract_datetime):
        return True
    bare_clock_time = _policy_core_current_message_clock_time_surface(current_message)
    if bare_clock_time:
        normalized_bare_variants = {
            bare_clock_time.casefold(),
            f"в {bare_clock_time}".casefold(),
            f"во {bare_clock_time}".casefold(),
            f"на {bare_clock_time}".casefold(),
            f"к {bare_clock_time}".casefold(),
            f"ко {bare_clock_time}".casefold(),
            f"после {bare_clock_time}".casefold(),
            f"до {bare_clock_time}".casefold(),
        }
        if contract_datetime.casefold() in normalized_bare_variants:
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
    return False


def _policy_core_contract_error_disallows_repair(
    schema_error: str | None,
    *,
    normalized_memory_profile: Mapping[str, Any] | None = None,
) -> bool:
    token = _policy_core_payload_token(schema_error)
    if token is None:
        return False
    if isinstance(normalized_memory_profile, Mapping):
        active_goal = _policy_core_payload_token(normalized_memory_profile.get("active_goal"))
        carry_contract = _policy_core_resume_pending_contract(
            normalized_memory_profile
        ) or _policy_core_active_pending_contract(normalized_memory_profile)
        if active_goal == "booking" and isinstance(carry_contract, Mapping):
            if token == "llm_policy_core_error:active_booking_info_interrupt_contract_invalid":
                return True
            if token.startswith("llm_policy_core_error:generic_info_interrupt_"):
                return True
    return any(
        token.startswith(prefix)
        for prefix in _NONREPAIRABLE_OWNER_SCHEMA_ERROR_PREFIXES
    )


def _policy_core_contract_error_disallows_boundary_rewrite(
    schema_error: str | None,
    *,
    normalized_memory_profile: Mapping[str, Any] | None = None,
) -> bool:
    token = _policy_core_payload_token(schema_error)
    if token in {
        "llm_policy_core_error:start_booking_exact_datetime_progression_required",
        "llm_policy_core_error:booking_availability_missing_service_reclassification_required",
    }:
        return False
    return _policy_core_contract_error_disallows_repair(
        schema_error,
        normalized_memory_profile=normalized_memory_profile,
    )


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
    if not (
        contract.slots.get("phone")
        or contract.slots.get("contact")
        or _policy_core_memory_slot_value(normalized_memory_profile, "phone")
        or _policy_core_memory_slot_value(normalized_memory_profile, "contact")
        or _policy_core_current_message_customer_phone_surface(current_message)
    ):
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
    if not _policy_core_booking_datetime_surface_is_executable(contract_datetime):
        return True
    contract_alternate_datetime = _policy_core_normalize_surface_text(
        contract.alternate_datetime
    )
    if not contract_alternate_datetime:
        return True
    if contract_alternate_datetime.casefold() != contract_datetime.casefold():
        return True
    if not _policy_core_booking_datetime_surface_is_executable(contract_alternate_datetime):
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
        contract.action == "collect"
        and contract.tool_action_hint == "collect"
        and contract.expected_reply_type == "phone"
        and contract.next_question == "phone"
        and list(contract.open_questions or []) == ["phone"]
    ):
        return False
    if _policy_core_calendar_book_slot_commit_contract_ready(
        contract,
        normalized_memory_profile,
    ):
        return False
    if not _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
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
    service_hint = _policy_core_resolve_current_message_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ) or (
        _policy_core_memory_grounded_service(normalized_memory_profile)
    )

    if contract.action == "fact" and contract.tool_action_hint == "consult":
        return "llm_policy_core_error:fact_consult_tool_action_invalid"

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
        contract.capability == "booking_manage"
        and contract.subject_kind == "booking"
        and contract.action == "fact"
        and contract.tool_action_hint in {"calendar.cancel", "calendar.reschedule"}
    ):
        return "llm_policy_core_error:booking_manage_admin_confirmation_handoff_required"

    if contract.intent == "booking" and contract.tool_action_hint == "calendar.book_slot":
        grounded_commit_inputs = bool(
            (grounded_service or service_hint)
            and (contract.slots.get("datetime") or _policy_core_memory_slot_value(normalized_memory_profile, "datetime"))
            and (contract.slots.get("name") or _policy_core_memory_slot_value(normalized_memory_profile, "name"))
        )
        has_contact = bool(
            contract.slots.get("phone")
            or contract.slots.get("contact")
            or _policy_core_memory_slot_value(normalized_memory_profile, "phone")
            or _policy_core_memory_slot_value(normalized_memory_profile, "contact")
        )
        if grounded_commit_inputs and not has_contact:
            return "llm_policy_core_error:booking_commit_contact_required"

    if (
        contract.tool_action_hint == "calendar.book_slot"
        and _policy_core_booking_commit_ready(contract, normalized_memory_profile)
        and contract.action != "fact"
    ):
        return "llm_policy_core_error:booking_commit_action_invalid"

    pending_contract = _policy_core_active_pending_contract(normalized_memory_profile)
    resume_contract = _policy_core_resume_pending_contract(normalized_memory_profile)
    carry_contract = resume_contract or pending_contract
    missing_service_exact_datetime_fact_interrupt_progression = (
        _policy_core_is_missing_service_exact_datetime_grounded_fact_interrupt_progression_context(
            contract,
            normalized_memory_profile,
            current_message=current_message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
    )

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
    missing_service_exact_datetime_service_choice_context = (
        _policy_core_has_missing_service_exact_datetime_service_choice_context(
            normalized_memory_profile
        )
    )
    if (
        missing_service_exact_datetime_fact_interrupt_progression
        and _policy_core_is_active_followup_info_interrupt(contract)
    ):
        signature = _policy_core_active_booking_info_interrupt_signature(contract)
        if signature is None:
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.action != "fact":
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.intent != signature["head_intent"]:
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.tool_action_hint != signature["tool_action_hint"]:
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if _policy_core_catalog_service_pack_refs(contract) != signature["pack_refs"]:
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.subject_kind != "service":
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.capability != signature["capability"]:
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if _policy_core_payload_token(contract.goal) != "booking":
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.resolution_mode != "policy_fact":
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.expected_reply_type != "name":
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.next_question != "name":
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if list(contract.open_questions or []) != ["name"]:
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.pending_question_act != "fill_requested_slot":
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.pending_question_target != "time":
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.active_question_relation != "generic_info_interrupt":
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        if contract.temporal_scope != "specific_time":
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
        carried_alternate_datetime = _policy_core_memory_alternate_datetime(
            normalized_memory_profile
        )
        contract_alternate_datetime = _policy_core_normalize_surface_text(
            contract.alternate_datetime
        )
        if (
            not isinstance(carried_alternate_datetime, str)
            or not carried_alternate_datetime
            or not isinstance(contract_alternate_datetime, str)
            or contract_alternate_datetime.casefold() != carried_alternate_datetime.casefold()
        ):
            return "llm_policy_core_error:missing_service_exact_datetime_grounded_fact_interrupt_progression_required"
    elif (
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
        if (
            missing_service_exact_datetime_service_choice_context
            and carry_reply_type == "service_choice"
        ):
            carried_alternate_datetime = _policy_core_memory_alternate_datetime(
                normalized_memory_profile
            )
            contract_alternate_datetime = _policy_core_normalize_surface_text(
                contract.alternate_datetime
            )
            if _policy_core_payload_token(contract.goal) != "booking":
                return "llm_policy_core_error:missing_service_exact_datetime_info_interrupt_carryover_invalid"
            if contract.subject_kind != "general":
                return "llm_policy_core_error:missing_service_exact_datetime_info_interrupt_carryover_invalid"
            if contract.resolution_mode != "policy_fact":
                return "llm_policy_core_error:missing_service_exact_datetime_info_interrupt_carryover_invalid"
            if contract.temporal_scope != "specific_time":
                return "llm_policy_core_error:missing_service_exact_datetime_info_interrupt_carryover_invalid"
            if (
                not isinstance(carried_alternate_datetime, str)
                or not carried_alternate_datetime
                or not isinstance(contract_alternate_datetime, str)
                or contract_alternate_datetime.casefold()
                != carried_alternate_datetime.casefold()
            ):
                return "llm_policy_core_error:missing_service_exact_datetime_info_interrupt_carryover_invalid"
            if _policy_core_contract_grounded_service(contract):
                return "llm_policy_core_error:missing_service_exact_datetime_info_interrupt_carryover_invalid"
            if contract.pending_question_act is not None:
                return "llm_policy_core_error:missing_service_exact_datetime_info_interrupt_carryover_invalid"
            if contract.pending_question_target is not None:
                return "llm_policy_core_error:missing_service_exact_datetime_info_interrupt_carryover_invalid"
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
        if contract.active_question_relation != "generic_info_interrupt":
            return (
                "llm_policy_core_error:active_followup_master_query_reclassification_required"
                if active_followup_master_query
                else "llm_policy_core_error:generic_info_interrupt_relation_invalid"
            )

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

    if _policy_core_contract_has_unsupported_service_booking_continuation_gap(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:unsupported_service_booking_continuation_requires_fact"

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

    if _policy_core_is_active_booking_info_interrupt_contract(
        contract,
        normalized_memory_profile,
    ):
        return "llm_policy_core_error:active_booking_info_interrupt_contract_invalid"

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

    if _policy_core_is_mixed_first_turn_hours_service_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:mixed_first_turn_hours_service_booking_followup_required"

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

    if _policy_core_is_service_query_multifact_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:service_query_multifact_booking_followup_required"

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
        if _policy_core_contract_has_unsupported_service_availability_grounding_gap(
            contract,
            current_message=current_message,
            context_payload=context_payload,
            client_slug=client_slug,
        ):
            return "llm_policy_core_error:unsupported_service_availability_grounding_required"
        expected_service_pack_ref = _policy_core_expected_catalog_service_pack_ref(contract)
        service_pack_refs = _policy_core_catalog_service_pack_refs(contract)
        expected_service_multifact_pack_refs = _policy_core_current_message_service_multifact_pack_refs(
            current_message,
            client_slug=client_slug,
        )
        expected_promotions_location_pack_refs = _policy_core_current_message_promotions_location_pack_refs(
            current_message
        )
        expected_promotions_booking_pack_refs = _policy_core_current_message_promotions_booking_collect_pack_refs(
            current_message,
            client_slug=client_slug,
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
        if (
            expected_promotions_booking_pack_refs
            and service_pack_refs == expected_promotions_booking_pack_refs
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
            and not _policy_core_is_canonical_mixed_first_turn_service_fact_booking_followup_contract(
                contract,
                normalized_memory_profile,
                current_message=current_message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
            and not _policy_core_is_canonical_mixed_first_turn_hours_service_booking_followup_contract(
                contract,
                normalized_memory_profile,
                current_message=current_message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
            and not _policy_core_is_canonical_mixed_first_turn_location_service_booking_followup_contract(
                contract,
                normalized_memory_profile,
                current_message=current_message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
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
            and not _policy_core_is_canonical_service_query_multifact_booking_followup_contract(
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


def _policy_core_grounded_service_repair_clause(grounded_service: str | None) -> str:
    if isinstance(grounded_service, str) and grounded_service:
        return (
            f'Preserve the grounded service through `referents.service.value="{grounded_service}"` '
            f'or `slots.service="{grounded_service}"`.'
        )
    return ""


def _policy_core_temporal_scope_repair_clause(temporal_scope: str | None) -> str:
    if isinstance(temporal_scope, str) and temporal_scope:
        return f'Preserve `temporal_scope="{temporal_scope}"`.'
    return ""


def _policy_core_alternate_datetime_repair_clause(alternate_datetime: str | None) -> str:
    if isinstance(alternate_datetime, str) and alternate_datetime:
        return f'Preserve `alternate_datetime="{alternate_datetime}"` exactly.'
    return ""


def _policy_core_promotions_subject_repair_clause(grounded_service: str | None) -> str:
    if isinstance(grounded_service, str) and grounded_service:
        return (
            f'Preserve the grounded service through `referents.service.value="{grounded_service}"` '
            f'or `slots.service="{grounded_service}"` and keep `subject_kind="service"`.'
        )
    return (
        'If no concrete service is grounded, keep `subject_kind="general"` and leave '
        '`slots.service` / `referents.service` empty.'
    )


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
    service_hint = _policy_core_resolve_current_message_service_hint(
        current_message=current_message,
        context_payload=context_payload,
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

    if token == "booking_manage_admin_confirmation_handoff_required":
        return (
            "The previous JSON attempted to execute cancel/reschedule from customer chat. "
            "For Beauty Salon v1, cancellation, reschedule, and admin-confirmation are "
            "confirmed by an administrator, not by the bot. Return "
            '`action="handoff"`, `tool_action_hint="handoff"`, `needs_manager=true`, '
            '`subject_kind="booking"`, `capability="booking_manage"`, and '
            '`resolution_mode="direct"`. Preserve grounded `referents.booking_ref`, '
            "customer/contact slots, and leave `expected_reply_type=null`, "
            "`next_question=null`, `open_questions=[]`. "
            "Omit `pending_question_act`, `pending_question_target`, and "
            "`active_question_relation`. Return corrected JSON only."
        )

    if token.startswith("focused_contract_mismatch"):
        mismatched_field = token.removeprefix("focused_contract_mismatch:").strip()
        field_clause = (
            f" Field `{mismatched_field}` did not match the focused contract."
            if mismatched_field
            else ""
        )
        return (
            "The previous JSON did not copy the governed focus_contract.forced_fields exactly."
            f"{field_clause} Return corrected JSON only and copy every forced field exactly; "
            "do not translate, typo-correct, rename, infer, omit, or semantically replace forced field values."
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

    if token == "booking_commit_contact_required":
        return (
            "The previous JSON tried to create a booking without a customer contact phone. "
            "A salon booking commit requires service, datetime, customer name, and phone. "
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, '
            '`expected_reply_type="phone"`, `next_question="phone"`, and `open_questions=["phone"]`. '
            "Preserve the grounded service, datetime, and name slots; do not call `calendar.book_slot` until phone is grounded. "
            "Return corrected JSON only."
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

    if token.startswith("fact_consult_tool_action_invalid"):
        parts = [
            "`tool_action_hint=\"consult\"` is only valid for consult/media collect turns, not for factual replies.",
            "Keep the same semantic meaning, but bind the fact turn to an executable tool.",
            "For unsupported or unconfirmed service availability questions, return `intent=\"services_overview\"` or `intent=\"out_of_domain\"`, `action=\"fact\"`, `tool_action_hint=\"catalog.service_query\"`, `pack_refs=[\"services_overview\"]`, `subject_kind=\"service\"` or `subject_kind=\"general\"`, `capability=\"other\"`, and `resolution_mode=\"policy_fact\"`.",
            "Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.",
            "Do not use `tool_action_hint=\"consult\"` unless the turn is `action=\"collect\"` with `expected_reply_type=\"media\"`.",
        ]
        if isinstance(current_message, str) and current_message.strip():
            parts.append(
                f'Ground any service candidate directly from the current message when present: "{current_message.strip()}".'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("unsupported_service_availability_grounding_required"):
        grounded_service = _policy_core_resolve_current_message_service_hint(
            current_message=current_message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
        service_candidate = _policy_core_unsupported_service_availability_candidate(
            current_message,
            grounded_service=grounded_service,
        )
        if not service_candidate:
            return None
        return (
            "The previous JSON invented or omitted the service referent for an unsupported service availability fact. "
            "Keep this as a standalone fact, not booking collection and not handoff. "
            'Return `intent="services_overview"` or `intent="out_of_domain"`, `action="fact"`, '
            '`tool_action_hint="catalog.service_query"`, `pack_refs=["services_overview"]`, '
            '`expected_reply_type=null`, `next_question=null`, `open_questions=[]`, '
            '`needs_manager=false`, `subject_kind="service"`, `capability="other"`, '
            '`resolution_mode="policy_fact"`, and clear pending follow-up fields. '
            f'Ground the unsupported service only from the current message as `slots.service="{service_candidate}"` '
            f'and `referents.service.value="{service_candidate}"`. '
            "Do not substitute a supported catalog service. Return corrected JSON only."
        )

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
            "If the user is asking to cancel, reschedule, change, or admin-confirm an existing booking, return `subject_kind=\"booking\"`, `capability=\"booking_manage\"`, `action=\"handoff\"`, `tool_action_hint=\"handoff\"`, and `needs_manager=true`; do NOT execute `calendar.cancel` or `calendar.reschedule` from customer chat.",
            "If the user is only asking to check or verify an existing booking without cancel/reschedule/admin-confirm, return `subject_kind=\"booking\"`, `capability=\"booking_manage\"`, `intent=\"check_booking\"` or `intent=\"verify_booking\"`, `action=\"fact\"`, and `tool_action_hint=\"calendar.get_booking\"`.",
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
            "Do NOT widen a single day/daypart clue like `завтра` to `date_range`; keep the precise grounded temporal scope.",
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
        has_booking_side_ask = _policy_core_current_message_has_temporal_booking_side_ask(current_message)
        template_id = (
            "mixed_first_turn_location_service_fact_booking_followup"
            if has_booking_side_ask
            else "mixed_first_turn_location_service_fact_scope"
        )
        pending_question_act = (
            "slot_constraint"
            if _policy_core_current_message_has_message_grounded_temporal_clue(current_message)
            else "ask_about_requested_slot"
        )
        return render_policy_core_generated_contract_repair_template(
            template_id,
            expected_pack_refs=json.dumps(expected_pack_refs, ensure_ascii=False),
            grounded_service_clause=_policy_core_grounded_service_repair_clause(grounded_service),
            pending_question_act=pending_question_act,
        )

    if token.startswith("mixed_first_turn_hours_service_booking_followup_required"):
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
        expected_pack_refs = _policy_core_current_message_hours_service_booking_followup_pack_refs(
            current_message,
            client_slug=client_slug,
        ) or ["hours", "pricing"]
        return render_policy_core_generated_contract_repair_template(
            "mixed_first_turn_hours_service_booking_followup",
            expected_pack_refs=json.dumps(expected_pack_refs, ensure_ascii=False),
            grounded_service_clause=_policy_core_grounded_service_repair_clause(grounded_service),
        )

    if token.startswith("mixed_first_turn_hours_location_fact_scope_required"):
        expected_booking_followup_pack_refs = (
            _policy_core_current_message_hours_location_booking_followup_pack_refs(
                current_message,
                client_slug=client_slug,
            )
        )
        if expected_booking_followup_pack_refs is not None:
            head_ref = (
                contract.intent
                if isinstance(contract, LlmPolicyCoreOutput) and contract.intent in {"hours", "location"}
                else "hours"
            )
            return render_policy_core_generated_contract_repair_template(
                "mixed_first_turn_hours_location_booking_followup",
                head_ref=head_ref,
                expected_pack_refs=json.dumps(expected_booking_followup_pack_refs, ensure_ascii=False),
            )
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
        return render_policy_core_generated_contract_repair_template(
            "mixed_first_turn_hours_location_fact_scope",
            scope_line=scope_line,
            extra_scope_line=extra_scope_line,
            head_ref=head_ref,
            expected_pack_refs=json.dumps(expected_pack_refs, ensure_ascii=False),
        )

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
        return render_policy_core_generated_contract_repair_template(
            "mixed_first_turn_service_fact_booking_side_precedence",
            expected_ref=expected_ref,
            expected_pack_refs=json.dumps([expected_ref], ensure_ascii=False),
            grounded_service_clause=_policy_core_grounded_service_repair_clause(grounded_service),
        )

    if token.startswith("service_query_multifact_booking_followup_required"):
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
        expected_pack_refs = _policy_core_current_message_service_multifact_booking_followup_pack_refs(
            current_message,
            client_slug=client_slug,
        ) or ["pricing", "duration"]
        head_ref = (
            contract.intent
            if isinstance(contract, LlmPolicyCoreOutput) and contract.intent in expected_pack_refs
            else expected_pack_refs[0]
        )
        head_intent = "master_query" if head_ref == "master" else head_ref
        pending_question_act = (
            contract.pending_question_act
            if isinstance(contract, LlmPolicyCoreOutput)
            and contract.pending_question_act in {"ask_about_requested_slot", "slot_constraint"}
            else "slot_constraint"
        )
        return render_policy_core_generated_contract_repair_template(
            "service_query_multifact_booking_followup",
            head_intent=head_intent,
            expected_pack_refs=json.dumps(expected_pack_refs, ensure_ascii=False),
            head_ref=head_ref,
            pending_question_act=pending_question_act,
            grounded_service_clause=_policy_core_grounded_service_repair_clause(grounded_service),
        )

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
        return render_policy_core_generated_contract_repair_template(
            "mixed_first_turn_hours_service_fact_scope",
            expected_pack_refs=json.dumps(expected_pack_refs, ensure_ascii=False),
            grounded_service_clause=_policy_core_grounded_service_repair_clause(grounded_service),
        )

    if token.startswith("mixed_first_turn_promotions_precedence_reclassification_required"):
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
        has_temporal_booking_side_ask = _policy_core_current_message_has_temporal_booking_side_ask(
            current_message
        )
        expected_pack_refs = (
            _policy_core_current_message_promotions_booking_collect_pack_refs(
                current_message,
                client_slug=client_slug,
            )
            if has_temporal_booking_side_ask
            else None
        ) or _policy_core_current_message_promotions_location_pack_refs(current_message) or [
            "promotions"
        ]
        if has_temporal_booking_side_ask and grounded_service:
            template_id = "mixed_first_turn_promotions_precedence_grounded_service_booking_followup"
        elif has_temporal_booking_side_ask:
            template_id = "mixed_first_turn_promotions_precedence_missing_service_booking_followup"
        else:
            template_id = "mixed_first_turn_promotions_precedence_fact_scope"
        return render_policy_core_generated_contract_repair_template(
            template_id,
            expected_pack_refs=json.dumps(expected_pack_refs, ensure_ascii=False),
            grounded_subject_clause=_policy_core_promotions_subject_repair_clause(grounded_service),
        )

    if token.startswith("promotions_booking_followup_reclassification_required"):
        expected_pack_refs = _policy_core_current_message_promotions_booking_collect_pack_refs(
            current_message,
            client_slug=client_slug,
        ) or ["promotions"]
        return render_policy_core_generated_contract_repair_template(
            "promotions_booking_followup",
            expected_pack_refs=json.dumps(expected_pack_refs, ensure_ascii=False),
        )

    if token.startswith("promotions_location_booking_followup_reclassification_required"):
        expected_pack_refs = _policy_core_current_message_promotions_booking_collect_pack_refs(
            current_message,
            client_slug=client_slug,
        ) or ["promotions", "location"]
        return render_policy_core_generated_contract_repair_template(
            "promotions_location_booking_followup",
            expected_pack_refs=json.dumps(expected_pack_refs, ensure_ascii=False),
        )

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
        expected_pack_refs = _policy_core_current_message_promotions_booking_collect_pack_refs(
            current_message,
            client_slug=client_slug,
        ) or ["promotions"]
        return render_policy_core_generated_contract_repair_template(
            "promotions_grounded_service_booking_followup",
            expected_pack_refs=json.dumps(expected_pack_refs, ensure_ascii=False),
            grounded_service_clause=_policy_core_grounded_service_repair_clause(grounded_service),
        )

    if token.startswith("unsupported_service_booking_continuation_requires_fact"):
        unsupported_service = _policy_core_memory_unsupported_service_fact(
            normalized_memory_profile
        )
        if not unsupported_service:
            return None
        return (
            "The previous JSON tried to continue booking for a service that was just classified as unsupported or unconfirmed. "
            "Until the user chooses a supported catalog service, this turn must remain a standalone service-availability fact, not booking collect and not handoff. "
            'Return `intent="services_overview"` or `intent="out_of_domain"`, `action="fact"`, '
            '`tool_action_hint="catalog.service_query"`, `pack_refs=["services_overview"]`, '
            '`subject_kind="service"`, `capability="other"`, `resolution_mode="policy_fact"`, '
            '`expected_reply_type=null`, `next_question=null`, `open_questions=[]`, '
            '`pending_question_act=null`, `pending_question_target=null`, `active_question_relation=null`, and `needs_manager=false`. '
            f'Preserve the unsupported service only as evidence: `slots.service="{unsupported_service}"` '
            f'and `referents.service.value="{unsupported_service}"`. '
            "Do not ask for booking slots and do not substitute a supported catalog service. Return corrected JSON only."
        )

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
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `subject_kind="booking"`, `capability="bookability"`, and `resolution_mode="direct"`.',
            'Set `expected_reply_type="name"`, `next_question="name"`, and `open_questions=["name"]`.',
            'Set `pending_question_act="fill_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="fill_requested_slot"`.',
            'Set `temporal_scope="specific_time"` and preserve the exact current-message datetime in BOTH `slots.datetime` and `alternate_datetime`.',
            'Do NOT ask for date/time again, do NOT leave `alternate_datetime=null`, remember that duplicating the exact datetime in both fields is required rather than redundant, and do NOT use `resolution_mode="live_calendar"` before the customer name is grounded.',
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
        return render_policy_core_generated_contract_repair_template(
            "active_booking_requested_slot_availability_followup",
            carry_reply_type=carry_reply_type,
            carry_next_question=carry_next_question,
            open_questions=json.dumps(
                _policy_core_expected_open_questions(carry_contract),
                ensure_ascii=False,
            ),
            carry_temporal_scope_clause=_policy_core_temporal_scope_repair_clause(
                _policy_core_memory_temporal_scope(normalized_memory_profile)
            ),
            carry_alternate_datetime_clause=_policy_core_alternate_datetime_repair_clause(
                _policy_core_memory_alternate_datetime(normalized_memory_profile)
            ),
        )

    if token.startswith("active_booking_info_interrupt_contract_invalid"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        if not isinstance(contract, LlmPolicyCoreOutput):
            return None
        signature = _policy_core_active_booking_info_interrupt_signature(contract)
        if signature is None:
            return None
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_memory_grounded_service(normalized_memory_profile)
        carry_pending_act = (
            carry_contract.get("pending_question_act")
            if isinstance(carry_contract.get("pending_question_act"), str)
            and carry_contract.get("pending_question_act").strip()
            else "ask_about_requested_slot"
        )
        carry_pending_target = (
            carry_contract.get("pending_question_target")
            if isinstance(carry_contract.get("pending_question_target"), str)
            and carry_contract.get("pending_question_target").strip()
            else "time"
        )
        expected_subject_kind = _policy_core_active_booking_info_interrupt_expected_subject_kind(
            signature,
            grounded_service=grounded_service,
        )
        return render_policy_core_generated_contract_repair_template(
            "active_booking_info_interrupt_contract",
            head_intent=signature["head_intent"],
            tool_action_hint=signature["tool_action_hint"],
            expected_pack_refs=json.dumps(signature["pack_refs"], ensure_ascii=False),
            expected_capability=signature["capability"],
            expected_subject_kind=expected_subject_kind,
            carry_reply_type=carry_reply_type,
            carry_next_question=carry_next_question,
            open_questions=json.dumps(
                _policy_core_expected_open_questions(carry_contract),
                ensure_ascii=False,
            ),
            carry_pending_act=carry_pending_act,
            carry_pending_target=carry_pending_target,
            carry_temporal_scope_clause=_policy_core_temporal_scope_repair_clause(
                _policy_core_memory_temporal_scope(normalized_memory_profile)
            ),
            carry_alternate_datetime_clause=_policy_core_alternate_datetime_repair_clause(
                _policy_core_memory_alternate_datetime(normalized_memory_profile)
            ),
            interrupt_subject_grounding_clause=_policy_core_active_booking_info_interrupt_grounding_clause(
                signature,
                grounded_service=grounded_service,
            ),
        )

    if token.startswith("active_booking_time_fill_progression_required"):
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or service_hint
        carried_alternate_datetime = _policy_core_memory_alternate_datetime(
            normalized_memory_profile
        )
        specialist_name = (
            _policy_core_contract_grounded_specialist(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_memory_grounded_specialist(normalized_memory_profile)
        parts: list[str] = [
            "The previous JSON kept an active booking on the datetime follow-up even though the current turn already supplied a concrete clock time.",
            "This turn must advance the booking slot-fill contract instead of asking for date/time again.",
            'Return `intent="booking"`, `action="collect"`, and `tool_action_hint="collect"`.',
            'Keep `subject_kind="booking"`, `capability="bookability"`, and `resolution_mode="direct"`.',
            'Set `expected_reply_type="name"`, `next_question="name"`, and `open_questions=["name"]`.',
            'Set `pending_question_act="fill_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="fill_requested_slot"`.',
            "Ground the completed datetime into both `slots.datetime` and `alternate_datetime` by combining the carried day/date context with the current exact clock time in the user's language surface.",
            "Use one executor-parseable exact datetime surface such as `завтра 17:45` or `завтра в 17:45`; do NOT keep stale daypart words together with the exact clock time.",
            "Do NOT keep `expected_reply_type=\"time\"`, `next_question=\"datetime\"`, `pending_question_act=\"slot_constraint\"`, `pending_question_target=\"specialist\"`, or `active_question_relation=\"referent_followup\"` once the requested time is grounded.",
            "Do NOT leave `alternate_datetime` as bare time-only text or translated carry-over.",
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `slots.service="{grounded_service}"` or `referents.service.value="{grounded_service}"`.'
            )
        if isinstance(specialist_name, str) and specialist_name:
            parts.append(
                f'Preserve the grounded specialist through `referents.specialist.value="{specialist_name}"`.'
            )
        if isinstance(carried_alternate_datetime, str) and carried_alternate_datetime:
            parts.append(
                f'Use the carried day/date surface from memory when composing the datetime, for example preserve `"{carried_alternate_datetime}"` instead of translating it.'
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
            'Mirror the same executor-parseable exact datetime surface into BOTH `slots.datetime` and `alternate_datetime`; do NOT keep stale daypart wording together with the exact clock time.',
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
            parts.append(
                "Use a parseable specific-time surface such as `завтра 18:00` or `завтра в 18:00` instead of `завтра вечером в 18:00`."
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
        if field_name == "name" and not _policy_core_memory_customer_name_surface_is_valid(cleaned):
            continue
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
        if semantic_contract.get("needs_human") is True:
            cleaned_contract["needs_human"] = True
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
                        if (
                            referent_key == "customer"
                            and target_key == "value"
                            and not _policy_core_memory_customer_name_surface_is_valid(raw_value)
                        ):
                            continue
                        row[target_key] = " ".join(raw_value.split())[
                            :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
                        ]
                if row and (
                    referent_key != "customer"
                    or row.get("value")
                    or row.get("entity_id")
                ):
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
    for key in ("capability_cards", "policy_cards", "service_cards", "consult_cards"):
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
    raw_grounding_hints = context_payload.get("message_grounding_hints")
    if isinstance(raw_grounding_hints, dict):
        compact_grounding_hints: dict[str, str] = {}
        for field_name in ("service",):
            compact_value = _trim_policy_core_context_text(
                raw_grounding_hints.get(field_name),
                max_chars=64,
            )
            if compact_value:
                compact_grounding_hints[field_name] = compact_value
        if compact_grounding_hints:
            normalized_context["message_grounding_hints"] = compact_grounding_hints
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


def _policy_core_boundary_normalization_semantic_view(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    view: dict[str, Any] = {}
    for field_name in (
        "intent",
        "action",
        "capability",
        "goal",
        "subject_kind",
        "resolution_mode",
        "expected_reply_type",
        "next_question",
        "pending_question_act",
        "pending_question_target",
        "active_question_relation",
    ):
        token = _policy_core_payload_token(payload.get(field_name))
        if token is not None:
            view[field_name] = token
    tool_action = _policy_core_payload_token(
        payload.get("tool_action") or payload.get("tool_action_hint")
    )
    if tool_action is not None:
        view["tool_action"] = tool_action
    reason = _policy_core_payload_reason_or_default(payload, default="")
    if reason:
        view["reason"] = reason
    pack_refs = _policy_core_payload_string_list(payload.get("pack_refs"))
    if pack_refs:
        view["pack_refs"] = pack_refs
    open_questions = _policy_core_payload_string_list(payload.get("open_questions"))
    if open_questions:
        view["open_questions"] = open_questions
    grounded_service = _policy_core_payload_grounded_service(payload)
    if grounded_service is not None:
        view["grounded_service"] = grounded_service
    semantic_slots = payload.get("slots")
    if isinstance(semantic_slots, Mapping):
        service = semantic_slots.get("service")
        if isinstance(service, str) and service.strip():
            view["service"] = service.strip()
    return view


def _policy_core_build_boundary_normalization_event(
    *,
    before_payload: Mapping[str, Any] | None,
    after_payload: Mapping[str, Any] | None,
    stage: str,
    template_id: str,
    trigger_reason: str,
) -> dict[str, Any] | None:
    before_view = _policy_core_boundary_normalization_semantic_view(before_payload)
    after_view = _policy_core_boundary_normalization_semantic_view(after_payload)
    if before_view == after_view:
        return None
    changes: dict[str, Any] = {}
    for field_name in sorted(set(before_view) | set(after_view)):
        before_value = before_view.get(field_name)
        after_value = after_view.get(field_name)
        if before_value == after_value:
            continue
        changes[field_name] = {
            "before": deepcopy(before_value),
            "after": deepcopy(after_value),
        }
    event = {
        "reason_code": _POLICY_CORE_BOUNDARY_SEMANTIC_NORMALIZATION_REASON_CODE,
        "stage": stage,
        "template_id": template_id,
        "trigger_reason": trigger_reason,
        "changes": changes,
    }
    for field_name in ("intent", "action", "tool_action", "expected_reply_type"):
        before_key = f"from_{field_name}"
        after_key = f"to_{field_name}"
        if before_view.get(field_name) is not None or after_view.get(field_name) is not None:
            event[before_key] = deepcopy(before_view.get(field_name))
            event[after_key] = deepcopy(after_view.get(field_name))
    return event


def _policy_core_sync_boundary_normalization_audit(result: dict[str, Any]) -> None:
    events = (
        list(result.get("boundary_normalization_events"))
        if isinstance(result.get("boundary_normalization_events"), list)
        else []
    )
    semantic_override_events: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, Mapping):
            continue
        changes = event.get("changes")
        if not isinstance(changes, Mapping):
            continue
        if not any(field_name in changes for field_name in ("intent", "action", "tool_action")):
            continue
        semantic_event = {
            "reason_code": event.get("reason_code"),
            "stage": event.get("stage"),
            "template_id": event.get("template_id"),
            "trigger_reason": event.get("trigger_reason"),
        }
        for field_name in ("intent", "action", "tool_action"):
            before_key = f"from_{field_name}"
            after_key = f"to_{field_name}"
            if before_key in event or after_key in event:
                semantic_event[before_key] = deepcopy(event.get(before_key))
                semantic_event[after_key] = deepcopy(event.get(after_key))
        semantic_override_events.append(semantic_event)
    if not semantic_override_events:
        result["semantic_intent_overrides"] = None
        result["semantic_arbiter_audit"] = None
        return
    reason_codes: list[str] = []
    for event in semantic_override_events:
        reason_code = event.get("reason_code")
        if isinstance(reason_code, str) and reason_code not in reason_codes:
            reason_codes.append(reason_code)
    result["semantic_intent_overrides"] = semantic_override_events
    result["semantic_arbiter_audit"] = {
        "intent_override_count": len(semantic_override_events),
        "intent_override_reason_codes": reason_codes,
        "action_changed": any(
            event.get("from_action") != event.get("to_action")
            for event in semantic_override_events
        ),
        "intent_changed": any(
            event.get("from_intent") != event.get("to_intent")
            for event in semantic_override_events
        ),
        "tool_action_changed": any(
            event.get("from_tool_action") != event.get("to_tool_action")
            for event in semantic_override_events
        ),
    }


def _policy_core_record_boundary_normalization(
    result: dict[str, Any],
    *,
    before_payload: Mapping[str, Any] | None,
    after_payload: Mapping[str, Any] | None,
    stage: str,
    template_id: str,
    trigger_reason: str,
) -> None:
    event = _policy_core_build_boundary_normalization_event(
        before_payload=before_payload,
        after_payload=after_payload,
        stage=stage,
        template_id=template_id,
        trigger_reason=trigger_reason,
    )
    if event is None:
        return
    events = list(result.get("boundary_normalization_events") or [])
    events.append(event)
    result["boundary_normalization_used"] = True
    result["boundary_normalization_events"] = events
    result["llm_policy_override_reason_code"] = (
        _POLICY_CORE_BOUNDARY_SEMANTIC_NORMALIZATION_REASON_CODE
    )
    reason_codes = list(result.get("llm_policy_override_reason_codes") or [])
    if _POLICY_CORE_BOUNDARY_SEMANTIC_NORMALIZATION_REASON_CODE not in reason_codes:
        reason_codes.append(_POLICY_CORE_BOUNDARY_SEMANTIC_NORMALIZATION_REASON_CODE)
    result["llm_policy_override_reason_codes"] = reason_codes
    _policy_core_sync_boundary_normalization_audit(result)


def _policy_core_apply_schema_boundary_normalizations(
    *,
    result: dict[str, Any],
    payload: dict[str, Any],
    contract: LlmPolicyCoreOutput | None,
    schema_error: str | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> tuple[dict[str, Any], LlmPolicyCoreOutput | None, str | None]:
    if _policy_core_contract_error_disallows_boundary_rewrite(
        schema_error,
        normalized_memory_profile=normalized_memory_profile,
    ):
        return payload, contract, schema_error
    normalization_specs: dict[str, tuple[tuple[str, Any], ...]] = {
        "llm_policy_core_error:mixed_first_turn_hours_location_fact_scope_required": (
            (
                "mixed_first_turn_hours_location_booking_followup_boundary",
                _policy_core_build_mixed_first_turn_hours_location_booking_followup_boundary_payload,
            ),
            (
                "mixed_first_turn_hours_location_fact_scope_boundary",
                _policy_core_build_mixed_first_turn_hours_location_fact_boundary_payload,
            ),
        ),
        "llm_policy_core_error:mixed_first_turn_location_service_fact_reclassification_required": (
            (
                "mixed_first_turn_location_service_fact_scope_boundary",
                _policy_core_build_mixed_first_turn_location_service_fact_boundary_payload,
            ),
        ),
        "llm_policy_core_error:mixed_first_turn_hours_service_booking_followup_required": (
            (
                "mixed_first_turn_hours_service_booking_followup_boundary",
                _policy_core_build_mixed_first_turn_hours_service_booking_followup_boundary_payload,
            ),
        ),
        "llm_policy_core_error:service_query_multifact_booking_followup_required": (
            (
                "service_query_multifact_booking_followup_boundary",
                _policy_core_build_service_query_multifact_booking_followup_boundary_payload,
            ),
        ),
        "llm_policy_core_error:service_query_multifact_reclassification_required": (
            (
                "service_query_multifact_scope_boundary",
                _policy_core_build_service_query_multifact_boundary_payload,
            ),
        ),
        "llm_policy_core_error:mixed_first_turn_service_fact_booking_side_precedence_required": (
            (
                "mixed_first_turn_service_fact_booking_side_precedence_boundary",
                _policy_core_build_mixed_first_turn_service_fact_booking_side_boundary_payload,
            ),
        ),
        "llm_policy_core_error:start_booking_exact_datetime_progression_required": (
            (
                "start_booking_exact_datetime_progression_boundary",
                _policy_core_build_start_booking_exact_datetime_boundary_payload,
            ),
        ),
        "llm_policy_core_error:booking_availability_missing_service_reclassification_required": (
            (
                "booking_availability_missing_service_boundary",
                _policy_core_build_booking_availability_missing_service_boundary_payload,
            ),
        ),
        "llm_policy_core_error:promotions_location_booking_followup_reclassification_required": (
            (
                "promotions_location_booking_followup_boundary",
                _policy_core_build_promotions_location_booking_followup_boundary_payload,
            ),
        ),
        "llm_policy_core_error:promotions_grounded_service_booking_followup_reclassification_required": (
            (
                "promotions_grounded_service_booking_followup_boundary",
                _policy_core_build_promotions_grounded_service_booking_followup_boundary_payload,
            ),
        ),
        "llm_policy_core_error:promotions_booking_followup_reclassification_required": (
            (
                "promotions_booking_followup_boundary",
                _policy_core_build_promotions_booking_fact_followup_boundary_payload,
            ),
        ),
        "llm_policy_core_error:mixed_first_turn_promotions_precedence_reclassification_required": (
            (
                "mixed_first_turn_promotions_precedence_fact_scope_boundary",
                _policy_core_build_mixed_first_turn_promotions_boundary_payload,
            ),
        ),
    }
    while isinstance(schema_error, str) and isinstance(payload, dict):
        builder_specs = normalization_specs.get(schema_error)
        if not builder_specs:
            break
        applied = False
        trigger_reason = schema_error
        for template_id, builder in builder_specs:
            normalized_payload = builder(
                payload=payload,
                normalized_memory_profile=normalized_memory_profile,
                current_message=current_message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
            if normalized_payload is None:
                continue
            before_payload = deepcopy(payload)
            payload = normalized_payload
            effective_template_id = template_id
            if (
                builder
                is _policy_core_build_mixed_first_turn_location_service_fact_boundary_payload
                and _policy_core_current_message_has_temporal_booking_side_ask(
                    current_message
                )
            ):
                effective_template_id = (
                    "mixed_first_turn_location_service_fact_booking_followup_boundary"
                )
            _policy_core_record_boundary_normalization(
                result,
                before_payload=before_payload,
                after_payload=payload,
                stage="runtime_contract",
                template_id=effective_template_id,
                trigger_reason=trigger_reason,
            )
            contract, schema_error = validate_llm_policy_core_output(payload)
            if contract is not None and schema_error is None:
                schema_error = _validate_policy_core_runtime_contract(
                    contract,
                    normalized_memory_profile=normalized_memory_profile,
                    current_message=current_message,
                    context_payload=context_payload,
                    client_slug=client_slug,
                )
            applied = True
            break
        if not applied:
            break
    return payload, contract, schema_error


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
        "boundary_normalization_used": False,
        "boundary_normalization_events": None,
        "llm_policy_override_reason_code": None,
        "llm_policy_override_reason_codes": None,
        "semantic_intent_overrides": None,
        "semantic_arbiter_audit": None,
        "focused_owner_contract_used": False,
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
    current_message_service_hint = _policy_core_resolve_current_message_service_hint(
        current_message=normalized,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    current_message_service_matches = _policy_core_context_service_matches(
        normalized,
        context_payload,
        client_slug=client_slug,
    )
    pack_runtime_service_matches = _policy_core_pack_runtime_service_matches(
        normalized,
        client_slug=client_slug,
    )
    if pack_runtime_service_matches:
        current_message_service_matches = list(
            dict.fromkeys(
                [
                    *current_message_service_matches,
                    *pack_runtime_service_matches,
                ]
            )
        )
    if current_message_service_hint:
        normalized_context_payload = dict(context_payload or {})
        raw_grounding_hints = normalized_context_payload.get("message_grounding_hints")
        grounding_hints = dict(raw_grounding_hints) if isinstance(raw_grounding_hints, dict) else {}
        grounding_hints["service"] = current_message_service_hint
        normalized_context_payload["message_grounding_hints"] = grounding_hints
        context_payload = normalized_context_payload
    policy_handoff_fields = _policy_core_policy_handoff_forced_fields(
        normalized_memory_profile,
        current_message=normalized,
        client_slug=client_slug,
        grounded_service=current_message_service_hint,
    )
    if policy_handoff_fields is not None:
        result["focused_policy_handoff"] = True
    standalone_booking_manage_fields = _policy_core_standalone_booking_manage_forced_fields(
        normalized_memory_profile,
        current_message=normalized,
        client_slug=client_slug,
    )
    if policy_handoff_fields is not None:
        standalone_booking_manage_fields = None
    elif standalone_booking_manage_fields is not None:
        result["focused_standalone_booking_manage"] = True
    booking_manage_reference_fields = None
    if policy_handoff_fields is None and standalone_booking_manage_fields is None:
        booking_manage_reference_fields = (
            _policy_core_booking_manage_reference_slot_carryover_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
            )
        )
        if booking_manage_reference_fields is not None:
            result["focused_booking_manage_reference_carryover"] = True
    multiple_service_booking_fields = None
    if (
        policy_handoff_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
    ):
        multiple_service_booking_fields = _policy_core_multiple_service_booking_forced_fields(
            normalized_memory_profile,
            current_message=normalized,
            service_matches=current_message_service_matches,
            client_slug=client_slug,
        )
        if multiple_service_booking_fields is not None:
            result["focused_multiple_service_booking"] = True
    standalone_service_fact_fields = None
    if (
        policy_handoff_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and multiple_service_booking_fields is None
    ):
        standalone_service_fact_fields = _policy_core_standalone_service_fact_forced_fields(
            normalized_memory_profile,
            current_message=normalized,
            grounded_service=current_message_service_hint,
            client_slug=client_slug,
        )
        if standalone_service_fact_fields is not None:
            standalone_service_fact_variant = resolve_policy_core_booking_info_interrupt_variant(
                intent=str(standalone_service_fact_fields["intent"]),
                capability=str(standalone_service_fact_fields["capability"]),
                pack_refs=tuple(standalone_service_fact_fields["pack_refs"]),
            )
            allowed_payload, context_payload = (
                _policy_core_narrow_missing_service_grounded_fact_interrupt_owner_envelope(
                    allowed_payload,
                    context_payload,
                    variant=standalone_service_fact_variant,
                )
            )
            result["focused_standalone_service_fact"] = standalone_service_fact_fields.get("intent")
    unsupported_service_availability_fields = None
    if (
        policy_handoff_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
    ):
        unsupported_service_availability_fields = (
            _policy_core_unsupported_service_availability_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
            )
        )
        if unsupported_service_availability_fields is not None:
            narrowed_allowed = dict(allowed_payload)
            raw_tool_actions = [
                action
                for action in list(narrowed_allowed.get("tool_actions") or [])
                if isinstance(action, str) and action.strip()
            ]
            narrowed_allowed["info_refs"] = ["services_overview"]
            narrowed_allowed["consult_refs"] = []
            narrowed_allowed["tool_actions"] = [
                action
                for action in ("catalog.service_query", "collect", "handoff")
                if action in raw_tool_actions
            ]
            narrowed_context = dict(context_payload) if isinstance(context_payload, Mapping) else {}
            narrowed_context.pop("consult_cards", None)
            allowed_payload = narrowed_allowed
            context_payload = narrowed_context or None
            result["focused_unsupported_service_availability"] = True
    unsupported_service_booking_continuation_fields = None
    if (
        policy_handoff_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
        and unsupported_service_availability_fields is None
    ):
        unsupported_service_booking_continuation_fields = (
            _policy_core_unsupported_service_booking_continuation_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
                client_slug=client_slug,
            )
        )
        if unsupported_service_booking_continuation_fields is not None:
            result["focused_unsupported_service_booking_continuation"] = True
    booking_manage_handoff_context_fields = None
    if (
        policy_handoff_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
        and unsupported_service_availability_fields is None
        and unsupported_service_booking_continuation_fields is None
    ):
        booking_manage_handoff_context_fields = (
            _policy_core_booking_manage_handoff_context_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
            )
        )
        if booking_manage_handoff_context_fields is not None:
            result["focused_booking_manage_handoff_context"] = True
    identity_first_booking_fields = None
    if (
        policy_handoff_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
        and unsupported_service_availability_fields is None
        and unsupported_service_booking_continuation_fields is None
        and booking_manage_handoff_context_fields is None
    ):
        handoff_context_contact_fields = _policy_core_handoff_context_contact_forced_fields(
            normalized_memory_profile,
            current_message=normalized,
        )
        if handoff_context_contact_fields is not None:
            result["focused_handoff_context_contact"] = True
        elif handoff_context_contact_fields is None:
            identity_first_booking_fields = _policy_core_identity_first_booking_collect_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
            )
    else:
        handoff_context_contact_fields = None
    if identity_first_booking_fields is not None:
        result["focused_identity_first_booking"] = True
    active_booking_contact_carryover_fields = None
    if (
        policy_handoff_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
        and unsupported_service_availability_fields is None
        and unsupported_service_booking_continuation_fields is None
        and booking_manage_handoff_context_fields is None
        and handoff_context_contact_fields is None
        and identity_first_booking_fields is None
    ):
        active_booking_contact_carryover_fields = (
            _policy_core_active_booking_contact_carryover_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
            )
        )
        if active_booking_contact_carryover_fields is not None:
            result["focused_active_booking_contact_carryover"] = True
    contextual_memory_service_exact_datetime_fields = None
    if (
        policy_handoff_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
        and unsupported_service_availability_fields is None
        and unsupported_service_booking_continuation_fields is None
        and booking_manage_handoff_context_fields is None
        and handoff_context_contact_fields is None
        and identity_first_booking_fields is None
        and active_booking_contact_carryover_fields is None
    ):
        contextual_memory_service_exact_datetime_fields = (
            _policy_core_contextual_memory_service_exact_datetime_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                client_slug=client_slug,
                grounded_service=current_message_service_hint,
            )
        )
        if contextual_memory_service_exact_datetime_fields is not None:
            result["focused_contextual_memory_service_exact_datetime"] = True
    unknown_service_booking_fields = None
    if (
        policy_handoff_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
        and unsupported_service_availability_fields is None
        and unsupported_service_booking_continuation_fields is None
        and booking_manage_handoff_context_fields is None
        and handoff_context_contact_fields is None
        and identity_first_booking_fields is None
        and active_booking_contact_carryover_fields is None
        and contextual_memory_service_exact_datetime_fields is None
    ):
        unknown_service_booking_fields = _policy_core_unknown_service_booking_forced_fields(
            normalized_memory_profile,
            current_message=normalized,
            client_slug=client_slug,
            grounded_service=current_message_service_hint,
        )
        if unknown_service_booking_fields is not None:
            result["focused_unknown_service_booking"] = True
    start_booking_exact_datetime_fields = None
    if (
        policy_handoff_fields is None
        and standalone_booking_manage_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
        and unsupported_service_availability_fields is None
        and unsupported_service_booking_continuation_fields is None
        and handoff_context_contact_fields is None
        and identity_first_booking_fields is None
        and active_booking_contact_carryover_fields is None
        and contextual_memory_service_exact_datetime_fields is None
        and unknown_service_booking_fields is None
    ):
        start_booking_exact_datetime_fields = (
            _policy_core_start_booking_exact_datetime_collect_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
                client_slug=client_slug,
            )
        )
    start_booking_exact_datetime_missing_service_fields = None
    if (
        policy_handoff_fields is not None
        or standalone_booking_manage_fields is not None
        or booking_manage_reference_fields is not None
        or multiple_service_booking_fields is not None
        or standalone_service_fact_fields is not None
        or unsupported_service_availability_fields is not None
        or unsupported_service_booking_continuation_fields is not None
        or booking_manage_handoff_context_fields is not None
        or handoff_context_contact_fields is not None
        or identity_first_booking_fields is not None
        or active_booking_contact_carryover_fields is not None
        or contextual_memory_service_exact_datetime_fields is not None
        or unknown_service_booking_fields is not None
    ):
        pass
    elif start_booking_exact_datetime_fields is not None:
        allowed_payload, context_payload = (
            _policy_core_narrow_start_booking_exact_datetime_owner_envelope(
                allowed_payload,
                context_payload,
            )
        )
        result["focused_start_booking_exact_datetime"] = True
    else:
        start_booking_exact_datetime_missing_service_fields = (
            _policy_core_start_booking_exact_datetime_missing_service_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
                client_slug=client_slug,
            )
        )
        if start_booking_exact_datetime_missing_service_fields is not None:
            allowed_payload, context_payload = (
                _policy_core_narrow_start_booking_exact_datetime_owner_envelope(
                    allowed_payload,
                    context_payload,
                )
            )
            result["focused_start_booking_exact_datetime_missing_service"] = True
    booking_availability_missing_service_fields = None
    if (
        start_booking_exact_datetime_fields is None
        and start_booking_exact_datetime_missing_service_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and policy_handoff_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
        and unsupported_service_availability_fields is None
        and unsupported_service_booking_continuation_fields is None
        and booking_manage_handoff_context_fields is None
        and handoff_context_contact_fields is None
        and identity_first_booking_fields is None
        and active_booking_contact_carryover_fields is None
        and contextual_memory_service_exact_datetime_fields is None
        and unknown_service_booking_fields is None
    ):
        booking_availability_missing_service_fields = (
            _policy_core_booking_availability_missing_service_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                context_payload=context_payload,
                client_slug=client_slug,
            )
        )
    if booking_availability_missing_service_fields is not None:
        allowed_payload, context_payload = (
            _policy_core_narrow_start_booking_exact_datetime_owner_envelope(
                allowed_payload,
                context_payload,
            )
        )
        result["focused_booking_availability_missing_service"] = True
    start_booking_service_collect_fields = None
    if (
        start_booking_exact_datetime_fields is None
        and start_booking_exact_datetime_missing_service_fields is None
        and booking_availability_missing_service_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and policy_handoff_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
        and unsupported_service_availability_fields is None
        and unsupported_service_booking_continuation_fields is None
        and booking_manage_handoff_context_fields is None
        and handoff_context_contact_fields is None
        and identity_first_booking_fields is None
        and active_booking_contact_carryover_fields is None
        and contextual_memory_service_exact_datetime_fields is None
        and unknown_service_booking_fields is None
    ):
        start_booking_service_collect_fields = (
            _policy_core_start_booking_service_collect_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
            )
        )
        if start_booking_service_collect_fields is not None:
            allowed_payload, context_payload = (
                _policy_core_narrow_start_booking_exact_datetime_owner_envelope(
                    allowed_payload,
                    context_payload,
                )
            )
            result["focused_start_booking_service_collect"] = True
    start_booking_partial_datetime_fields = None
    if (
        start_booking_exact_datetime_fields is None
        and start_booking_exact_datetime_missing_service_fields is None
        and booking_availability_missing_service_fields is None
        and start_booking_service_collect_fields is None
        and standalone_booking_manage_fields is None
        and booking_manage_reference_fields is None
        and policy_handoff_fields is None
        and multiple_service_booking_fields is None
        and standalone_service_fact_fields is None
        and unsupported_service_availability_fields is None
        and unsupported_service_booking_continuation_fields is None
        and booking_manage_handoff_context_fields is None
        and handoff_context_contact_fields is None
        and identity_first_booking_fields is None
        and active_booking_contact_carryover_fields is None
        and contextual_memory_service_exact_datetime_fields is None
        and unknown_service_booking_fields is None
    ):
        start_booking_partial_datetime_fields = (
            _policy_core_start_booking_partial_datetime_collect_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
                client_slug=client_slug,
            )
        )
        if start_booking_partial_datetime_fields is not None:
            allowed_payload, context_payload = (
                _policy_core_narrow_start_booking_exact_datetime_owner_envelope(
                    allowed_payload,
                    context_payload,
                )
            )
            result["focused_start_booking_partial_datetime"] = True
    focused_interrupt_variant = _policy_core_resolve_missing_service_grounded_fact_interrupt_variant(
        normalized_memory_profile,
        current_message=normalized,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    if focused_interrupt_variant is not None:
        allowed_payload, context_payload = (
            _policy_core_narrow_missing_service_grounded_fact_interrupt_owner_envelope(
                allowed_payload,
                context_payload,
                variant=focused_interrupt_variant,
            )
        )
        result["focused_interrupt_variant"] = focused_interrupt_variant.head_intent
    active_booking_phone_fill_fields = (
        _policy_core_active_booking_phone_fill_forced_fields(
            normalized_memory_profile,
            current_message=normalized,
        )
    )
    if active_booking_phone_fill_fields is not None:
        result["focused_active_booking_phone_fill"] = True
    active_booking_time_pending_ack_fields = (
        _policy_core_active_booking_time_pending_ack_forced_fields(
            normalized_memory_profile,
            current_message=normalized,
        )
    )
    if active_booking_time_pending_ack_fields is not None:
        result["focused_active_booking_time_pending_ack"] = True
    active_booking_partial_datetime_fields = None
    if active_booking_time_pending_ack_fields is None:
        active_booking_partial_datetime_fields = (
            _policy_core_active_booking_partial_datetime_collect_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
            )
        )
    if active_booking_partial_datetime_fields is not None:
        result["focused_active_booking_partial_datetime"] = True
    active_booking_time_fill_fields = None
    if (
        active_booking_time_pending_ack_fields is None
        and active_booking_partial_datetime_fields is None
    ):
        active_booking_time_fill_fields = _policy_core_active_booking_time_fill_forced_fields(
            normalized_memory_profile,
            current_message=normalized,
        )
    if active_booking_time_fill_fields is not None:
        result["focused_active_booking_time_fill"] = True
    active_booking_service_datetime_fill_fields = None
    if (
        active_booking_time_pending_ack_fields is None
        and active_booking_partial_datetime_fields is None
        and active_booking_time_fill_fields is None
    ):
        active_booking_service_datetime_fill_fields = (
            _policy_core_active_booking_service_datetime_fill_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
            )
        )
        if active_booking_service_datetime_fill_fields is not None:
            result["focused_active_booking_service_datetime_fill"] = True
    active_booking_service_fill_fields = None
    if (
        active_booking_time_pending_ack_fields is None
        and active_booking_partial_datetime_fields is None
        and active_booking_time_fill_fields is None
        and active_booking_service_datetime_fill_fields is None
        and focused_interrupt_variant is None
    ):
        active_booking_service_fill_fields = (
            _policy_core_active_booking_service_fill_forced_fields(
                normalized_memory_profile,
                grounded_service=current_message_service_hint,
            )
        )
        if active_booking_service_fill_fields is not None:
            result["focused_active_booking_service_fill"] = True
    service_choice_slot_carryover_fields = None
    if (
        active_booking_time_pending_ack_fields is None
        and active_booking_partial_datetime_fields is None
        and active_booking_time_fill_fields is None
        and active_booking_service_datetime_fill_fields is None
        and active_booking_service_fill_fields is None
        and focused_interrupt_variant is None
    ):
        service_choice_slot_carryover_fields = (
            _policy_core_service_choice_slot_carryover_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
            )
        )
        if service_choice_slot_carryover_fields is not None:
            result["focused_service_choice_slot_carryover"] = True
    specialist_relaxation_fields = None
    if (
        active_booking_time_pending_ack_fields is None
        and active_booking_partial_datetime_fields is None
        and active_booking_time_fill_fields is None
        and active_booking_service_datetime_fill_fields is None
        and active_booking_service_fill_fields is None
        and service_choice_slot_carryover_fields is None
    ):
        specialist_relaxation_fields = (
            _policy_core_specialist_relaxation_collect_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                client_slug=client_slug,
            )
        )
        if specialist_relaxation_fields is not None:
            result["focused_specialist_relaxation"] = True
    active_booking_info_interrupt_fields = None
    if (
        active_booking_time_pending_ack_fields is None
        and active_booking_partial_datetime_fields is None
        and active_booking_time_fill_fields is None
        and active_booking_service_datetime_fill_fields is None
        and active_booking_service_fill_fields is None
        and specialist_relaxation_fields is None
    ):
        active_booking_info_interrupt_fields = (
            _policy_core_active_booking_info_interrupt_forced_fields(
                normalized_memory_profile,
                current_message=normalized,
                grounded_service=current_message_service_hint,
                client_slug=client_slug,
            )
        )
        if active_booking_info_interrupt_fields is not None:
            result["focused_active_booking_info_interrupt"] = (
                active_booking_info_interrupt_fields.get("intent")
            )
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
    (
        full_prompt_min_tokens_override,
        full_prompt_safe_cap_override,
    ) = _policy_core_gpt5_token_profile_for_turn(
        normalized_memory_profile,
        compact_mode=False,
        focused_interrupt_variant=focused_interrupt_variant,
    )
    (
        compact_prompt_min_tokens_override,
        compact_prompt_safe_cap_override,
    ) = _policy_core_gpt5_token_profile_for_turn(
        normalized_memory_profile,
        compact_mode=True,
        focused_interrupt_variant=focused_interrupt_variant,
    )
    compact_first_blocked = _policy_core_blocks_compact_first_attempt(
        normalized_memory_profile,
        current_message=normalized,
        client_slug=client_slug,
    )
    if (
        policy_handoff_fields is not None
        or standalone_booking_manage_fields is not None
        or booking_manage_reference_fields is not None
        or multiple_service_booking_fields is not None
        or standalone_service_fact_fields is not None
        or unsupported_service_availability_fields is not None
        or unsupported_service_booking_continuation_fields is not None
        or booking_manage_handoff_context_fields is not None
        or handoff_context_contact_fields is not None
        or identity_first_booking_fields is not None
        or active_booking_contact_carryover_fields is not None
        or contextual_memory_service_exact_datetime_fields is not None
        or unknown_service_booking_fields is not None
        or start_booking_exact_datetime_fields is not None
        or start_booking_exact_datetime_missing_service_fields is not None
        or start_booking_partial_datetime_fields is not None
        or start_booking_service_collect_fields is not None
        or active_booking_phone_fill_fields is not None
        or active_booking_time_pending_ack_fields is not None
        or active_booking_partial_datetime_fields is not None
        or active_booking_time_fill_fields is not None
        or active_booking_service_datetime_fill_fields is not None
        or active_booking_service_fill_fields is not None
        or service_choice_slot_carryover_fields is not None
        or specialist_relaxation_fields is not None
        or active_booking_info_interrupt_fields is not None
    ):
        compact_first_blocked = True
    if focused_interrupt_variant is not None:
        compact_first_blocked = False
    compact_first_attempt = not compact_first_blocked and (
        POLICY_CORE_COMPACT_FIRST_ATTEMPT
        or policy_timeout_seconds <= POLICY_CORE_COMPACT_TRIGGER_TIMEOUT_SECONDS
        or _policy_core_prefers_compact_first_attempt(normalized_memory_profile)
    )
    use_compact_messages = compact_first_attempt
    structured_output_enabled = _policy_core_structured_output_enabled()
    result["structured_output_enabled"] = structured_output_enabled
    from app.services.policy_vocabulary_snapshot_service import (
        build_policy_core_response_format,
    )

    focused_response_format_fields = _policy_core_active_booking_commit_forced_fields(
        normalized_memory_profile,
        current_message=normalized,
    )
    if (
        focused_response_format_fields is None
        and active_booking_phone_fill_fields is not None
    ):
        focused_response_format_fields = active_booking_phone_fill_fields
    if (
        focused_response_format_fields is None
        and policy_handoff_fields is not None
    ):
        focused_response_format_fields = policy_handoff_fields
    if (
        focused_response_format_fields is None
        and standalone_booking_manage_fields is not None
    ):
        focused_response_format_fields = standalone_booking_manage_fields
    if (
        focused_response_format_fields is None
        and booking_manage_reference_fields is not None
    ):
        focused_response_format_fields = booking_manage_reference_fields
    if (
        focused_response_format_fields is None
        and multiple_service_booking_fields is not None
    ):
        focused_response_format_fields = multiple_service_booking_fields
    if (
        focused_response_format_fields is None
        and standalone_service_fact_fields is not None
    ):
        focused_response_format_fields = standalone_service_fact_fields
    if (
        focused_response_format_fields is None
        and unsupported_service_availability_fields is not None
    ):
        focused_response_format_fields = unsupported_service_availability_fields
    if (
        focused_response_format_fields is None
        and unsupported_service_booking_continuation_fields is not None
    ):
        focused_response_format_fields = unsupported_service_booking_continuation_fields
    if (
        focused_response_format_fields is None
        and booking_manage_handoff_context_fields is not None
    ):
        focused_response_format_fields = booking_manage_handoff_context_fields
    if (
        focused_response_format_fields is None
        and handoff_context_contact_fields is not None
    ):
        focused_response_format_fields = handoff_context_contact_fields
    if (
        focused_response_format_fields is None
        and identity_first_booking_fields is not None
    ):
        focused_response_format_fields = identity_first_booking_fields
    if (
        focused_response_format_fields is None
        and active_booking_contact_carryover_fields is not None
    ):
        focused_response_format_fields = active_booking_contact_carryover_fields
    if (
        focused_response_format_fields is None
        and contextual_memory_service_exact_datetime_fields is not None
    ):
        focused_response_format_fields = contextual_memory_service_exact_datetime_fields
    if (
        focused_response_format_fields is None
        and unknown_service_booking_fields is not None
    ):
        focused_response_format_fields = unknown_service_booking_fields
    if (
        focused_response_format_fields is None
        and active_booking_time_pending_ack_fields is not None
    ):
        focused_response_format_fields = active_booking_time_pending_ack_fields
    if (
        focused_response_format_fields is None
        and active_booking_partial_datetime_fields is not None
    ):
        focused_response_format_fields = active_booking_partial_datetime_fields
    if (
        focused_response_format_fields is None
        and active_booking_time_fill_fields is not None
    ):
        focused_response_format_fields = active_booking_time_fill_fields
    if (
        focused_response_format_fields is None
        and active_booking_service_datetime_fill_fields is not None
    ):
        focused_response_format_fields = active_booking_service_datetime_fill_fields
    if (
        focused_response_format_fields is None
        and active_booking_service_fill_fields is not None
    ):
        focused_response_format_fields = active_booking_service_fill_fields
    if (
        focused_response_format_fields is None
        and service_choice_slot_carryover_fields is not None
    ):
        focused_response_format_fields = service_choice_slot_carryover_fields
    if (
        focused_response_format_fields is None
        and specialist_relaxation_fields is not None
    ):
        focused_response_format_fields = specialist_relaxation_fields
    if (
        focused_response_format_fields is None
        and active_booking_info_interrupt_fields is not None
    ):
        focused_response_format_fields = active_booking_info_interrupt_fields
    if focused_response_format_fields is not None:
        compact_first_blocked = True
    if (
        focused_response_format_fields is None
        and start_booking_exact_datetime_fields is not None
    ):
        focused_response_format_fields = start_booking_exact_datetime_fields
    if (
        focused_response_format_fields is None
        and start_booking_exact_datetime_missing_service_fields is not None
    ):
        focused_response_format_fields = start_booking_exact_datetime_missing_service_fields
    if (
        focused_response_format_fields is None
        and start_booking_partial_datetime_fields is not None
    ):
        focused_response_format_fields = start_booking_partial_datetime_fields
    if (
        focused_response_format_fields is None
        and booking_availability_missing_service_fields is not None
    ):
        focused_response_format_fields = booking_availability_missing_service_fields
    if (
        focused_response_format_fields is None
        and start_booking_service_collect_fields is not None
    ):
        focused_response_format_fields = start_booking_service_collect_fields
    if focused_response_format_fields is None:
        focused_response_format_fields = (
            _policy_core_missing_service_grounded_fact_interrupt_forced_fields(
                normalized_memory_profile,
                variant=focused_interrupt_variant,
                grounded_service=current_message_service_hint,
            )
            if focused_interrupt_variant is not None
            else None
        )
    if structured_output_enabled and focused_response_format_fields is not None:
        policy_response_format = {"type": "json_object"}
        result["focused_response_format_mode"] = "json_object"
    elif structured_output_enabled:
        policy_response_format = build_policy_core_response_format(
            allowed_tool_actions,
            forced_field_values=None,
        )
    else:
        policy_response_format = None
    if focused_response_format_fields is not None:
        focused_policy_input = _build_policy_core_focused_input(
            policy_input,
            focused_response_format_fields,
        )
        result["policy_input"] = deepcopy(focused_policy_input)
        focused_allowed_payload = focused_policy_input.get("allowed")
        if isinstance(focused_allowed_payload, Mapping):
            allowed_tool_actions = list(
                focused_allowed_payload.get("tool_actions") or []
            )
            allowed_info_refs = list(focused_allowed_payload.get("info_refs") or [])
            allowed_consult_refs = list(
                focused_allowed_payload.get("consult_refs") or []
            )
        messages = _build_policy_core_messages(
            _POLICY_CORE_FOCUSED_PROMPT,
            focused_policy_input,
        )
        compact_messages = None
        compact_first_attempt = False
        use_compact_messages = False
        compact_first_blocked = True
        full_prompt_min_tokens_override = POLICY_CORE_GPT5_FOCUSED_SAFE_MAX_TOKENS
        full_prompt_safe_cap_override = POLICY_CORE_GPT5_FOCUSED_SAFE_MAX_TOKENS
        compact_prompt_min_tokens_override = POLICY_CORE_GPT5_FOCUSED_SAFE_MAX_TOKENS
        compact_prompt_safe_cap_override = POLICY_CORE_GPT5_FOCUSED_SAFE_MAX_TOKENS
        result["focused_owner_contract_used"] = True
    sticky_full_prompt_retry = (
        focused_response_format_fields is not None or compact_first_blocked
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
        retry_timeout = (
            policy_timeout_seconds
            if focused_response_format_fields is not None
            else _resolve_policy_core_governed_retry_timeout_seconds(
                policy_timeout_seconds,
                sticky_full_prompt_retry=sticky_full_prompt_retry,
            )
        )
        if retry_timeout > 0 and (
            sticky_full_prompt_retry or retry_timeout not in timeout_attempts
        ):
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
        min_tokens_override=full_prompt_min_tokens_override,
        safe_cap_override=full_prompt_safe_cap_override,
    )
    transient_retry_used = False
    structured_output_fallback_used = False
    last_attempt_used_compact = False

    def _focused_full_retry_messages() -> list[dict[str, str]]:
        retry_instruction = _build_policy_core_focused_contract_retry_instruction(
            focused_response_format_fields
        )
        if not retry_instruction:
            return messages
        retry_messages = list(messages)
        retry_messages.append({"role": "user", "content": retry_instruction})
        return retry_messages

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
            min_tokens_override=full_prompt_min_tokens_override,
            safe_cap_override=full_prompt_safe_cap_override,
        )
        retry_messages = _focused_full_retry_messages()
        last_messages_for_attempt = retry_messages
        compact_retry_used = True
        result["compact_retry_used"] = True
        try:
            response = llm.generate(
                messages=retry_messages,
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
                    messages=retry_messages,
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
            min_tokens_override=(
                compact_prompt_min_tokens_override
                if attempt_uses_compact
                else full_prompt_min_tokens_override
            ),
            safe_cap_override=(
                compact_prompt_safe_cap_override
                if attempt_uses_compact
                else full_prompt_safe_cap_override
            ),
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
                if not attempt_uses_compact and not sticky_full_prompt_retry:
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
                        if not attempt_uses_compact and not sticky_full_prompt_retry:
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
                        and (
                            classified_error
                            in {"connection_error", "provider_unavailable", "service_unavailable"}
                            or (
                                focused_response_format_fields is not None
                                and classified_error == "error"
                            )
                        )
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
                and (
                    classified_error
                    in {"connection_error", "provider_unavailable", "service_unavailable"}
                    or (
                        focused_response_format_fields is not None
                        and classified_error == "error"
                    )
                )
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
        fallback_use_compact = False if sticky_full_prompt_retry else use_compact_messages or compact_input_used
        if not fallback_use_compact and not sticky_full_prompt_retry:
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
                min_tokens_override=(
                    compact_prompt_min_tokens_override
                    if fallback_use_compact
                    else full_prompt_min_tokens_override
                ),
                safe_cap_override=(
                    compact_prompt_safe_cap_override
                    if fallback_use_compact
                    else full_prompt_safe_cap_override
                ),
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
            empty_response_retry_timeout_seconds = _resolve_policy_core_empty_response_retry_timeout_seconds(
                timeout_seconds_used
            )
            timeout_during_empty_response_recovery = False

            def _attempt_empty_response_recovery(
                *,
                stage: str,
                use_response_format: bool,
                messages_override: list[dict[str, str]] | None = None,
            ) -> bool:
                nonlocal response
                nonlocal attempt_count
                nonlocal content
                nonlocal structured_output_fallback_used
                nonlocal timeout_seconds_used
                nonlocal last_messages_for_attempt
                nonlocal timeout_during_empty_response_recovery
                retry_messages = messages_override or last_messages_for_attempt
                if not _should_attempt_llm(
                    timing_context,
                    timeout_seconds=empty_response_retry_timeout_seconds,
                    stage=stage,
                ):
                    return False
                retry_kwargs = {
                    "messages": retry_messages,
                    "max_tokens": max_tokens_used,
                    "model": model_name_used,
                    "timeout_seconds": empty_response_retry_timeout_seconds,
                    "temperature": temperature_used,
                    "reasoning_effort": reasoning_effort_used,
                }
                if use_response_format:
                    retry_kwargs["response_format"] = policy_response_format
                try:
                    response = llm.generate(**retry_kwargs)
                except httpx.TimeoutException:
                    timeout_during_empty_response_recovery = True
                    return False
                attempt_count += 1
                timeout_seconds_used = empty_response_retry_timeout_seconds
                last_messages_for_attempt = retry_messages
                content = (response.content or "").strip() if response else ""
                if content:
                    structured_output_fallback_used = True
                    result["structured_output_fallback_used"] = True
                    return True
                return False

            focused_retry_messages: list[dict[str, str]] | None = None
            if focused_response_format_fields is None:
                _attempt_empty_response_recovery(
                    stage="policy_core_empty_response_plain_retry",
                    use_response_format=False,
                )
            else:
                retry_instruction = _build_policy_core_focused_contract_retry_instruction(
                    focused_response_format_fields
                )
                if retry_instruction:
                    # Focused rows already have a strict schema. When the provider returns an
                    # empty structured body, repeating the exact same prompt is wasted budget;
                    # the next governed retry should add the canonical contract reminder.
                    focused_retry_messages = list(last_messages_for_attempt)
                    focused_retry_messages.append({"role": "user", "content": retry_instruction})
                    _attempt_empty_response_recovery(
                        stage="policy_core_focused_empty_response_contract_retry",
                        use_response_format=True,
                        messages_override=focused_retry_messages,
                    )
                else:
                    _attempt_empty_response_recovery(
                        stage="policy_core_empty_response_structured_retry",
                        use_response_format=True,
                    )
                if not content:
                    _attempt_empty_response_recovery(
                        stage="policy_core_focused_empty_response_plain_retry",
                        use_response_format=False,
                        messages_override=focused_retry_messages,
                    )
            if not content and timeout_during_empty_response_recovery:
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
    focused_contract_error = _policy_core_focused_contract_error(
        payload,
        focused_response_format_fields,
    )
    if focused_contract_error:
        result["focused_contract_error"] = focused_contract_error
        contract = None
        schema_error = focused_contract_error
    else:
        prevalidate_input_payload = deepcopy(payload)
        payload, prevalidate_template_id = _policy_core_apply_prevalidate_boundary_normalizations(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
        if prevalidate_template_id is not None:
            _policy_core_record_boundary_normalization(
                result,
                before_payload=prevalidate_input_payload,
                after_payload=payload,
                stage="prevalidate",
                template_id=prevalidate_template_id,
                trigger_reason="prevalidate_boundary_normalization",
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
            prevalidate_input_payload = deepcopy(payload)
            payload, prevalidate_template_id = _policy_core_apply_prevalidate_boundary_normalizations(
                payload=payload,
                normalized_memory_profile=normalized_memory_profile,
                current_message=message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
            if prevalidate_template_id is not None:
                _policy_core_record_boundary_normalization(
                    result,
                    before_payload=prevalidate_input_payload,
                    after_payload=payload,
                    stage="prevalidate",
                    template_id=prevalidate_template_id,
                    trigger_reason="prevalidate_boundary_normalization",
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
    if schema_error:
        retry_content = _retry_full_prompt_after_compact_failure()
        if retry_content:
            content = retry_content
            result["raw"] = content
            payload = _parse_policy_core_content(content)
            if not isinstance(payload, dict):
                result["error"] = "invalid_json"
                logger.warning(
                    "LLM policy core returned invalid JSON after runtime-contract full retry",
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
            prevalidate_input_payload = deepcopy(payload)
            payload, prevalidate_template_id = _policy_core_apply_prevalidate_boundary_normalizations(
                payload=payload,
                normalized_memory_profile=normalized_memory_profile,
                current_message=message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
            if prevalidate_template_id is not None:
                _policy_core_record_boundary_normalization(
                    result,
                    before_payload=prevalidate_input_payload,
                    after_payload=payload,
                    stage="prevalidate",
                    template_id=prevalidate_template_id,
                    trigger_reason="prevalidate_boundary_normalization",
                )
            if tool_args_sanitized:
                result["tool_args_sanitized"] = True
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
    payload, contract, schema_error = _policy_core_apply_schema_boundary_normalizations(
        result=result,
        payload=payload,
        contract=contract,
        schema_error=schema_error,
        normalized_memory_profile=normalized_memory_profile,
        current_message=message,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    if schema_error:
        repair_instruction = None
        if not _policy_core_contract_error_disallows_repair(
            schema_error,
            normalized_memory_profile=normalized_memory_profile,
        ):
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
                        prevalidate_input_payload = deepcopy(payload)
                        payload, prevalidate_template_id = _policy_core_apply_prevalidate_boundary_normalizations(
                            payload=payload,
                            normalized_memory_profile=normalized_memory_profile,
                            current_message=message,
                            context_payload=context_payload,
                            client_slug=client_slug,
                        )
                        if prevalidate_template_id is not None:
                            _policy_core_record_boundary_normalization(
                                result,
                                before_payload=prevalidate_input_payload,
                                after_payload=payload,
                                stage="prevalidate",
                                template_id=prevalidate_template_id,
                                trigger_reason="prevalidate_boundary_normalization",
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
                        payload, contract, schema_error = (
                            _policy_core_apply_schema_boundary_normalizations(
                                result=result,
                                payload=payload,
                                contract=contract,
                                schema_error=schema_error,
                                normalized_memory_profile=normalized_memory_profile,
                                current_message=message,
                                context_payload=context_payload,
                                client_slug=client_slug,
                            )
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
