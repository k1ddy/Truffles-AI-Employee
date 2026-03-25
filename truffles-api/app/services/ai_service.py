import hashlib
import json
import os
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Iterator, List, Optional, Tuple
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.logging_config import get_logger, record_llm_time, record_rag_time, start_span
from app.models import Client, Message, Prompt
from app.schemas.consult import ConsultControllerOutput, ConsultTopic, validate_consult_controller_output
from app.services.alert_service import alert_error
from app.services.knowledge_service import format_knowledge_context, search_knowledge
from app.services.llm import OpenAIProvider
from app.services.pack_runtime_service import get_system_lexicon_list
from app.services.result import Result

logger = get_logger("ai_service")
_INTENT_SIGNAL_OVERRIDE: ContextVar[dict[str, object] | None] = ContextVar(
    "intent_signal_override",
    default=None,
)

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.85
MID_CONFIDENCE_THRESHOLD = 0.5
# Minimum RAG score to consider knowledge reliable (legacy name used in tests)
KNOWLEDGE_CONFIDENCE_THRESHOLD = MID_CONFIDENCE_THRESHOLD

# Common short-form greetings/thanks/acknowledgements.
GREETING_PHRASES = {
    "привет",
    "здравствуйте",
    "добрый день",
    "добрый вечер",
    "доброе утро",
    "салам",
    "сәлем",
    "салют",
    "дд",
}
GREETING_FILLER_TOKENS = {
    "плз",
    "плиз",
    "пожалуйста",
    "пж",
    "пжл",
    "pls",
    "plz",
    "please",
}
LOW_SIGNAL_FILLER_TOKENS = {
    "плз",
    "пжл",
    "плиз",
    "пж",
    "pls",
    "plz",
    "спс",
    "срочно",
}

THANKS_PHRASES = {
    "спасибо",
    "благодарю",
    "спасибо большое",
    "пожалуйста",
}

ACKNOWLEDGEMENT_PHRASES = {
    "ок",
    "окей",
    "ok",
    "okay",
    "ага",
    "угу",
    "понял",
    "поняла",
    "понятно",
    "ясно",
    "хорошо",
    "норм",
}

WHITELISTED_PHRASES = GREETING_PHRASES | THANKS_PHRASES | ACKNOWLEDGEMENT_PHRASES

CONFIRMATION_PHRASES = {
    "да",
    "нет",
    "ага",
    "угу",
    "неа",
    "не",
}

YES_NO_QUESTION_HINTS = {
    "имеете в виду",
    "правильно понимаю",
    "верно",
    "если да",
    "если нет",
    "есть ли",
    "можно ли",
    "нужно ли",
    "подтвердите",
    "да или нет",
}

OPEN_QUESTION_HINTS = {
    "что",
    "какой",
    "какая",
    "какие",
    "сколько",
    "когда",
    "где",
    "почему",
    "как",
    "уточните",
    "напишите",
    "выберите",
    "назовите",
    "укажите",
    "адрес",
    "дата",
    "время",
    "имя",
}

ACKNOWLEDGEMENT_RESPONSE = "Ок. Если нужно — подскажу по услугам, ценам или записи."
LOW_SIGNAL_RESPONSE = "Понял. Можете уточнить, что именно вас интересует?"
GREETING_RESPONSE = "Здравствуйте! Могу помочь с услугами, ценами или записью."
THANKS_RESPONSE = "Рад помочь. Если нужно — подскажу по услугам, ценам или записи."
BOT_STATUS_RESPONSE = "Я на связи. Напишите ваш вопрос, и я помогу."
OUT_OF_DOMAIN_RESPONSE = (
    "Я помогаю по салону: услуги, запись и цены. "
    "По услугам, записи и ценам — спрашивайте."
)
PENDING_SYSTEM_HINT = (
    "Контекст: у клиента уже открыт запрос на менеджера. "
    "Отвечай кратко, уточняй детали (услуга/дата/время/имя), "
    "но не давай финальных решений и не обещай результат."
)

YES_CONFIRMATION_PHRASES = {
    "да",
    "ага",
    "угу",
    "ок",
    "окей",
    "okay",
    "yes",
    "иә",
    "ия",
    "конечно",
    "давай",
    "подключай",
    "подключите",
}

NO_CONFIRMATION_PHRASES = {
    "нет",
    "неа",
    "no",
    "не",
    "жоқ",
    "жок",
    "не надо",
    "не нужно",
    "не хочу",
    "не сейчас",
    "потом",
}

REFUSAL_PHRASES = (
    "не хочу",
    "не буду",
    "не стану",
    "не скажу",
    "не назову",
    "не дам",
    "не оставлю",
    "не сообщу",
    "не готов",
    "не готова",
)

REFUSAL_NAME_TOKENS = ("имя", "имени")
REFUSAL_PHONE_TOKENS = ("телефон", "номер", "номера")

BOT_STATUS_KEYWORDS = {
    "бот не отвечает",
    "бот молчит",
    "не отвечает",
    "не ответил",
    "почему не отвечает",
    "почему не отвечаете",
    "почему молчит",
    "почему молчите",
    "бот молчит",
    "молчишь",
    "молчите",
    "ты здесь",
    "ты тут",
    "ты еще здесь",
    "ты ещё здесь",
    "вы здесь",
    "вы тут",
    "вы еще здесь",
    "вы ещё здесь",
    "на связи",
    "есть кто",
    "кто-нибудь здесь",
    "алло",
}

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
FAST_MODEL = os.environ.get("FAST_MODEL", "gpt-5-mini")
SLOW_MODEL = os.environ.get("SLOW_MODEL", "gpt-5-mini")
FAST_MODEL_MAX_CHARS = int(os.environ.get("FAST_MODEL_MAX_CHARS", "160"))
INTENT_TIMEOUT_SECONDS = float(os.environ.get("INTENT_TIMEOUT_SECONDS", "1.5"))
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "6"))
LLM_RETRY_TIMEOUT_SECONDS = float(os.environ.get("LLM_RETRY_TIMEOUT_SECONDS", "3.0"))
LLM_RETRY_ON_TIMEOUT = os.environ.get("LLM_RETRY_ON_TIMEOUT")
LLM_RETRY_ON_TRANSIENT = os.environ.get("LLM_RETRY_ON_TRANSIENT")
LLM_TIMEOUT_FALLBACK_MODEL = os.environ.get("LLM_TIMEOUT_FALLBACK_MODEL", FAST_MODEL)
SERVICE_REWRITE_TIMEOUT_SECONDS = float(os.environ.get("SERVICE_REWRITE_TIMEOUT_SECONDS", "1.2"))
SERVICE_REWRITE_MAX_TOKENS = int(os.environ.get("SERVICE_REWRITE_MAX_TOKENS", "80"))
RAG_REWRITE_TIMEOUT_SECONDS = float(os.environ.get("RAG_REWRITE_TIMEOUT_SECONDS", "1.0"))
RAG_REWRITE_MAX_TOKENS = int(os.environ.get("RAG_REWRITE_MAX_TOKENS", "80"))
MULTI_INTENT_TIMEOUT_SECONDS = float(os.environ.get("MULTI_INTENT_TIMEOUT_SECONDS", "1.2"))
MULTI_INTENT_RETRY_TIMEOUT_SECONDS = float(os.environ.get("MULTI_INTENT_RETRY_TIMEOUT_SECONDS", "2.4"))
MULTI_INTENT_RETRY_ON_TIMEOUT = os.environ.get("MULTI_INTENT_RETRY_ON_TIMEOUT")
MULTI_INTENT_MAX_TOKENS = int(os.environ.get("MULTI_INTENT_MAX_TOKENS", "120"))
CONSULT_CONTROLLER_TIMEOUT_SECONDS = float(
    os.environ.get("CONSULT_CONTROLLER_TIMEOUT_SECONDS", "1.8")
)
CONSULT_CONTROLLER_MAX_TOKENS = int(os.environ.get("CONSULT_CONTROLLER_MAX_TOKENS", "220"))
ASR_PRIMARY_PROVIDER = os.environ.get("ASR_PRIMARY_PROVIDER", "elevenlabs")
ASR_FALLBACK_PROVIDER = os.environ.get("ASR_FALLBACK_PROVIDER", "openai_whisper")
ASR_TIMEOUT_SECONDS = float(os.environ.get("ASR_TIMEOUT_SECONDS", "6"))
ASR_MIN_CHARS = int(os.environ.get("ASR_MIN_CHARS", "12"))
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_ASR_URL = "https://api.elevenlabs.io/v1/speech-to-text"
ELEVENLABS_ASR_MODEL_ID = (
    os.environ.get("ASR_ELEVENLABS_MODEL_ID")
    or os.environ.get("ELEVENLABS_ASR_MODEL_ID")
    or "scribe_v1"
)
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "600"))
MAX_HISTORY_MESSAGES = int(os.environ.get("LLM_HISTORY_MESSAGES", "6"))
HIERARCHICAL_MEMORY_ENABLED = os.environ.get("LLM_HIER_MEMORY_ENABLED", "1")
HIERARCHICAL_MEMORY_SUMMARY_MESSAGES = int(os.environ.get("LLM_HIER_SUMMARY_MESSAGES", "6"))
HIERARCHICAL_MEMORY_SUMMARY_MAX_LINES = int(os.environ.get("LLM_HIER_SUMMARY_MAX_LINES", "4"))
HIERARCHICAL_MEMORY_SUMMARY_MAX_CHARS = int(os.environ.get("LLM_HIER_SUMMARY_MAX_CHARS", "320"))
MAX_KNOWLEDGE_CHARS = int(os.environ.get("LLM_KNOWLEDGE_CHARS", "1500"))
LLM_CACHE_TTL_SECONDS = int(os.environ.get("LLM_CACHE_TTL_SECONDS", "86400"))
CONSULT_LLM_TIMEOUT_SECONDS = float(os.environ.get("CONSULT_LLM_TIMEOUT_SECONDS", "6"))
CONSULT_LLM_MAX_TOKENS = int(os.environ.get("CONSULT_LLM_MAX_TOKENS", "220"))
LLM_CACHE_PREFIX = "truffles:llm_cache"
LLM_CACHE_SOCKET_TIMEOUT_SECONDS = float(os.environ.get("LLM_CACHE_SOCKET_TIMEOUT_SECONDS", "0.3"))
REDIS_URL = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
POLICY_VERSION = os.environ.get("POLICY_VERSION", "v1")
LLM_BUDGET_PREFIX = "truffles:llm_budget"
LLM_BUDGET_SOCKET_TIMEOUT_SECONDS = float(os.environ.get("LLM_BUDGET_SOCKET_TIMEOUT_SECONDS", "0.3"))
RAG_SEARCH_MIN_BUDGET_MS = 500.0
CONSULT_DISALLOWED_PATTERNS = [
    r"\bцена\b",
    r"\bстоим",
    r"\bстоимость",
    r"\bпрайс",
    r"\bзапис",
    r"\bзапиш",
    r"\bадрес\b",
    r"\bмастер",
    r"\bадминистратор",
    r"\bскидк",
    r"\bакци",
    r"\bоплат",
    r"\bкаспи",
    r"\bу нас\b",
    r"\bв салоне\b",
    r"\bмы делаем\b",
    r"\bмы оказываем\b",
    r"\bмы предостав",
]

# Global LLM provider instance
_llm_provider = None
_llm_cache_client = None
_llm_cache_url = None
_llm_budget_client = None
_llm_budget_url = None


def _normalize_api_key(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if cleaned.casefold() in {"none", "null"}:
        return None
    return cleaned or None


def _current_openai_api_key() -> str | None:
    """Resolve API key from env first and keep provider in sync."""
    global OPENAI_API_KEY, _llm_provider
    raw_env_key = os.environ.get("OPENAI_API_KEY")
    env_override = raw_env_key is not None
    env_key = _normalize_api_key(raw_env_key)
    fallback_key = _normalize_api_key(OPENAI_API_KEY)
    # Explicit env override (including empty string) should disable fallback key.
    resolved_key = env_key if env_override else fallback_key
    if resolved_key != fallback_key:
        OPENAI_API_KEY = resolved_key
        _llm_provider = None
    return resolved_key


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _classify_generation_error(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ReadError,
            httpx.RemoteProtocolError,
            httpx.NetworkError,
        ),
    ):
        return "provider_unavailable"
    message = str(exc).strip().lower()
    if any(
        token in message
        for token in (
            "timeout",
            "timed out",
            "deadline",
            "readtimeout",
            "connecttimeout",
        )
    ):
        return "timeout"
    if any(
        token in message
        for token in (
            "connection error",
            "connection reset",
            "service unavailable",
            "temporarily unavailable",
            "bad gateway",
            "gateway timeout",
            "rate limit",
            "429",
            "502",
            "503",
            "504",
        )
    ):
        return "provider_unavailable"
    return "exception"


def _is_transient_generation_error(error_code: str | None) -> bool:
    return error_code in {"provider_unavailable"}


def _resolve_generation_retry_timeout(base_timeout: float) -> float:
    retry_timeout = max(0.1, LLM_RETRY_TIMEOUT_SECONDS)
    return min(retry_timeout, max(base_timeout, 0.1))


def _resolve_multi_intent_retry_timeout(base_timeout: float) -> float:
    retry_timeout = max(0.1, MULTI_INTENT_RETRY_TIMEOUT_SECONDS)
    return max(base_timeout, retry_timeout)


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
    stage_key = stage.strip().lower()
    client_slug = context.get("client_slug")
    if stage_key.endswith("llm_ms"):
        record_llm_time(client_slug, stage_key, elapsed_ms)
    elif stage_key == "rag_ms":
        record_rag_time(client_slug, elapsed_ms)
    logger.info("Timing", extra={"context": context})


def _start_rag_span(timing_context: dict | None, *, client_slug: str | None, branch_id: str | None):
    context: dict = {}
    if isinstance(timing_context, dict):
        context.update(timing_context)
    if isinstance(client_slug, str) and client_slug:
        context.setdefault("client_slug", client_slug)
    if branch_id:
        context.setdefault("branch_id", branch_id)
    return start_span("rag.search", context=context)


def _remaining_pipeline_budget_ms(timing_context: dict | None) -> float | None:
    if not isinstance(timing_context, dict):
        return None
    deadline = timing_context.get("pipeline_deadline")
    if not isinstance(deadline, (int, float)):
        return None
    remaining_ms = (deadline - time.monotonic()) * 1000
    return max(0.0, remaining_ms)


def _record_pipeline_budget_skip(
    *,
    timing_context: dict | None,
    stage: str,
    required_ms: float,
    remaining_ms: float,
) -> None:
    if not isinstance(timing_context, dict):
        return
    timing = timing_context.get("timing")
    if not isinstance(timing, dict):
        timing = {}
    budget = timing.get("budget")
    if not isinstance(budget, dict):
        budget = {}
    skips = budget.get("skips")
    if not isinstance(skips, list):
        skips = []
    skips.append(
        {
            "stage": stage,
            "required_ms": round(required_ms, 2),
            "remaining_ms": round(remaining_ms, 2),
        }
    )
    budget["skips"] = skips
    budget["budget_ms"] = timing_context.get("pipeline_budget_ms")
    budget["remaining_ms"] = round(remaining_ms, 2)
    timing["budget"] = budget
    timing_context["timing"] = timing


def _should_attempt_stage(
    timing_context: dict | None,
    *,
    required_ms: float,
    stage: str,
    degrade_reason: str | None = "deadline_exceeded",
) -> bool:
    remaining_ms = _remaining_pipeline_budget_ms(timing_context)
    if remaining_ms is None:
        return True
    if remaining_ms >= required_ms:
        return True
    _record_pipeline_budget_skip(
        timing_context=timing_context,
        stage=stage,
        required_ms=required_ms,
        remaining_ms=remaining_ms,
    )
    if isinstance(timing_context, dict) and degrade_reason:
        timing_context["llm_degradation_reason"] = degrade_reason
    return False


def _simulation_llm_allowed(timing_context: dict | None) -> bool:
    if not isinstance(timing_context, dict):
        return True
    sim_context = timing_context.get("simulation")
    if not isinstance(sim_context, dict):
        return True
    if sim_context.get("mode") is False:
        return True
    llm_allowed = sim_context.get("llm_allowed")
    if llm_allowed is None:
        return False
    return bool(llm_allowed)


def _should_attempt_llm(
    timing_context: dict | None,
    *,
    timeout_seconds: float,
    stage: str,
) -> bool:
    if not _simulation_llm_allowed(timing_context):
        if isinstance(timing_context, dict):
            timing_context["llm_degradation_reason"] = "llm_skip"
        return False
    required_ms = max(float(timeout_seconds) * 1000, 0.0)
    return _should_attempt_stage(
        timing_context,
        required_ms=required_ms,
        stage=stage,
    )


def _split_consult_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip() for part in parts if part and part.strip()]


def _contains_disallowed_consult(text: str) -> bool:
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    for pattern in CONSULT_DISALLOWED_PATTERNS:
        if re.search(pattern, normalized):
            return True
    return False


def _filter_consult_advice(text: str) -> str | None:
    if not text:
        return None
    cleaned = text.strip().strip('"').strip()
    if not cleaned:
        return None
    sentences = _split_consult_sentences(cleaned)
    if not sentences:
        return None
    allowed = [sentence for sentence in sentences if not _contains_disallowed_consult(sentence)]
    if not allowed:
        return None
    combined = " ".join(allowed).strip()
    return _trim_text(combined, 420)


def get_llm_provider() -> OpenAIProvider:
    """Get or create LLM provider instance."""
    global _llm_provider
    api_key = _current_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    if _llm_provider is None:
        _llm_provider = OpenAIProvider(api_key=api_key, default_model=FAST_MODEL)
    return _llm_provider


def _get_llm_cache_client():
    global _llm_cache_client, _llm_cache_url
    if redis is None:
        return None
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return None
    if not _is_env_enabled(os.environ.get("LLM_CACHE_ENABLED"), default=True):
        return None
    if _llm_cache_client is None or _llm_cache_url != REDIS_URL:
        _llm_cache_url = REDIS_URL
        _llm_cache_client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=LLM_CACHE_SOCKET_TIMEOUT_SECONDS,
            socket_connect_timeout=LLM_CACHE_SOCKET_TIMEOUT_SECONDS,
        )
    return _llm_cache_client


def _get_llm_budget_client():
    global _llm_budget_client, _llm_budget_url
    if redis is None:
        return None
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return None
    if _llm_budget_client is None or _llm_budget_url != REDIS_URL:
        _llm_budget_url = REDIS_URL
        _llm_budget_client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=LLM_BUDGET_SOCKET_TIMEOUT_SECONDS,
            socket_connect_timeout=LLM_BUDGET_SOCKET_TIMEOUT_SECONDS,
        )
    return _llm_budget_client


def _coerce_positive_int(value: object) -> int | None:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _get_llm_budget_config(client_config: dict | None) -> dict:
    if not isinstance(client_config, dict):
        return {}
    budget = client_config.get("llm_budget")
    return budget if isinstance(budget, dict) else {}


def _seconds_until_utc_day_end(now: datetime) -> int:
    next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds = int((next_day - now).total_seconds())
    return max(seconds, 60)


def _append_llm_budget_event(timing_context: dict | None, budget_meta: dict) -> None:
    if timing_context is None or not isinstance(budget_meta, dict):
        return
    active = bool(budget_meta.get("active"))
    allowed = bool(budget_meta.get("allowed", True))
    if not active and allowed:
        return
    timing_context.setdefault("llm_budget_events", []).append(budget_meta)


def _resolve_client_config(db: Session, client_id: UUID, timing_context: dict | None) -> dict | None:
    if timing_context and isinstance(timing_context.get("client_config"), dict):
        return timing_context.get("client_config")
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
    except Exception as exc:
        logger.warning(f"LLM budget client lookup failed: {exc}")
        return None
    if client and isinstance(client.config, dict):
        return client.config
    return None


def consume_llm_budget(
    *,
    client_slug: str,
    client_config: dict | None,
    scope: str,
    now: datetime | None = None,
) -> dict:
    budget = _get_llm_budget_config(client_config)
    daily_max_calls = _coerce_positive_int(budget.get("daily_max_calls"))
    if daily_max_calls is None:
        return {
            "allowed": True,
            "reason": "unlimited",
            "limit": None,
            "count": None,
            "window": "daily",
            "scope": scope,
            "active": False,
        }

    cache = _get_llm_budget_client()
    if not cache:
        return {
            "allowed": True,
            "reason": "redis_unavailable",
            "limit": daily_max_calls,
            "count": None,
            "window": "daily",
            "scope": scope,
            "active": True,
        }

    now = now or datetime.now(timezone.utc)
    day_key = now.strftime("%Y%m%d")
    key = f"{LLM_BUDGET_PREFIX}:{client_slug}:{day_key}"
    try:
        count = cache.incr(key)
        if count == 1:
            cache.expire(key, _seconds_until_utc_day_end(now))
    except Exception as exc:
        logger.warning(f"LLM budget counter failed: {exc}")
        return {
            "allowed": True,
            "reason": "redis_error",
            "limit": daily_max_calls,
            "count": None,
            "window": "daily",
            "scope": scope,
            "active": True,
        }

    allowed = count <= daily_max_calls
    return {
        "allowed": allowed,
        "reason": "allow" if allowed else "budget_exceeded",
        "limit": daily_max_calls,
        "count": int(count),
        "window": "daily",
        "scope": scope,
        "active": True,
    }


def _build_llm_cache_key(text: str, client_slug: str, policy_version: str) -> str:
    normalized = normalize_for_matching(text)
    raw_key = f"{client_slug}:{policy_version}:{normalized}"
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return f"{LLM_CACHE_PREFIX}:{client_slug}:{policy_version}:{digest}"


def _read_llm_cache(text: str, client_slug: str) -> tuple[str | None, str | None]:
    cache = _get_llm_cache_client()
    if not cache:
        return None, None
    key = _build_llm_cache_key(text, client_slug, POLICY_VERSION)
    try:
        payload = cache.get(key)
    except Exception as exc:
        logger.warning(f"LLM cache read failed: {exc}")
        return None, None
    if not payload:
        return None, None
    try:
        data = json.loads(payload)
    except Exception as exc:
        logger.warning(f"LLM cache decode failed: {exc}")
        return None, None
    response = data.get("response") if isinstance(data, dict) else None
    confidence = data.get("confidence") if isinstance(data, dict) else None
    if not isinstance(response, str) or not response.strip():
        return None, None
    if not isinstance(confidence, str) or not confidence.strip():
        confidence = None
    return response, confidence


def _write_llm_cache(text: str, client_slug: str, response: str, confidence: str) -> None:
    if not response:
        return
    cache = _get_llm_cache_client()
    if not cache:
        return
    key = _build_llm_cache_key(text, client_slug, POLICY_VERSION)
    payload = json.dumps({"response": response, "confidence": confidence}, ensure_ascii=False)
    try:
        cache.setex(key, LLM_CACHE_TTL_SECONDS, payload)
    except Exception as exc:
        logger.warning(f"LLM cache write failed: {exc}")


def _select_generation_model(user_message: str, max_score: float) -> tuple[str, str]:
    normalized = normalize_for_matching(user_message)
    if normalized and len(normalized) > FAST_MODEL_MAX_CHARS and max_score < MID_CONFIDENCE_THRESHOLD:
        return SLOW_MODEL, "slow"
    return FAST_MODEL, "fast"


def _trim_text(text: str, max_chars: int) -> str:
    if not text or max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    trimmed = text[:max_chars]
    if "\n" in trimmed:
        trimmed = trimmed.rsplit("\n", 1)[0]
    return trimmed.rstrip()


def transcribe_audio(
    audio_bytes: bytes,
    *,
    filename: str,
    mime_type: Optional[str] = None,
    model: Optional[str] = None,
    language: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
) -> Optional[str]:
    """Transcribe short audio to text. Returns None on failure."""
    if not _current_openai_api_key():
        logger.warning("Audio transcription skipped: OPENAI_API_KEY missing")
        return None

    provider = get_llm_provider()
    if not hasattr(provider, "transcribe_audio"):
        logger.warning("Audio transcription skipped: provider lacks transcribe_audio")
        return None

    try:
        transcript = provider.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=filename,
            mime_type=mime_type,
            model=model,
            language=language,
            timeout_seconds=timeout_seconds,
        )
        cleaned = (transcript or "").strip()
        return cleaned or None
    except Exception as exc:
        logger.warning(f"Audio transcription failed: {exc}")
        return None


def _normalize_asr_provider(provider: str | None) -> str | None:
    if not provider:
        return None
    cleaned = provider.strip().lower()
    if cleaned in {"openai", "openai_whisper", "whisper"}:
        return "openai_whisper"
    if cleaned in {"elevenlabs", "eleven_labs"}:
        return "elevenlabs"
    return cleaned


def _is_valid_transcript(text: str | None, min_chars: int) -> bool:
    if not text:
        return False
    cleaned = text.strip()
    if not cleaned:
        return False
    if min_chars <= 0:
        return True
    return len(cleaned) >= min_chars


def _transcribe_with_openai(
    *,
    audio_bytes: bytes,
    filename: str,
    mime_type: Optional[str],
    model: Optional[str],
    language: Optional[str],
    timeout_seconds: float | None,
) -> tuple[str | None, str | None]:
    if not _current_openai_api_key():
        return None, "missing_openai_key"
    provider = get_llm_provider()
    if not hasattr(provider, "transcribe_audio"):
        return None, "provider_missing_transcribe"
    try:
        transcript = provider.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=filename,
            mime_type=mime_type,
            model=model,
            language=language,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        logger.warning(f"OpenAI transcription failed: {exc}")
        return None, "openai_error"
    cleaned = (transcript or "").strip()
    return cleaned or None, None


def _transcribe_with_elevenlabs(
    *,
    audio_bytes: bytes,
    filename: str,
    mime_type: Optional[str],
    language: Optional[str],
    timeout_seconds: float | None,
) -> tuple[str | None, str | None]:
    if not ELEVENLABS_API_KEY:
        return None, "missing_elevenlabs_key"
    files = {"file": (filename or "audio", audio_bytes, mime_type or "application/octet-stream")}
    data: dict[str, str] = {"model_id": ELEVENLABS_ASR_MODEL_ID}
    if language:
        data["language_code"] = language
    try:
        with httpx.Client(timeout=timeout_seconds or 10.0) as client:
            response = client.post(
                ELEVENLABS_ASR_URL,
                headers={"xi-api-key": ELEVENLABS_API_KEY},
                files=files,
                data=data or None,
            )
    except Exception as exc:
        logger.warning(f"ElevenLabs transcription failed: {exc}")
        return None, "elevenlabs_error"
    if response.status_code != 200:
        logger.warning(
            f"ElevenLabs transcription error: {response.status_code} - {response.text[:200]}"
        )
        return None, "elevenlabs_status"
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        transcript = payload.get("text") or payload.get("transcript") or payload.get("transcription")
    else:
        transcript = None
    cleaned = (transcript or "").strip()
    if not cleaned:
        logger.warning("ElevenLabs transcription returned empty text")
    return cleaned or None, None


def transcribe_audio_with_fallback(
    audio_bytes: bytes,
    *,
    filename: str,
    mime_type: Optional[str] = None,
    model: Optional[str] = None,
    language: Optional[str] = None,
    primary_provider: str | None = None,
    fallback_provider: str | None = None,
    timeout_seconds: float | None = None,
    min_chars: int | None = None,
) -> tuple[str | None, dict, str]:
    primary = _normalize_asr_provider(primary_provider or ASR_PRIMARY_PROVIDER)
    fallback = _normalize_asr_provider(fallback_provider or ASR_FALLBACK_PROVIDER)
    timeout = ASR_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    min_chars = ASR_MIN_CHARS if min_chars is None else min_chars

    meta = {
        "asr_used": False,
        "asr_provider": None,
        "asr_fallback_used": False,
        "asr_failed": False,
        "asr_text_len": 0,
        "asr_model": None,
    }

    if not primary:
        meta["asr_failed"] = True
        return None, meta, "missing_primary_provider"

    transcript = None
    error = None
    if primary == "openai_whisper":
        openai_model = model or "whisper-1"
        transcript, error = _transcribe_with_openai(
            audio_bytes=audio_bytes,
            filename=filename,
            mime_type=mime_type,
            model=openai_model,
            language=language,
            timeout_seconds=timeout,
        )
        meta["asr_model"] = openai_model
    elif primary == "elevenlabs":
        transcript, error = _transcribe_with_elevenlabs(
            audio_bytes=audio_bytes,
            filename=filename,
            mime_type=mime_type,
            language=language,
            timeout_seconds=timeout,
        )
        meta["asr_model"] = ELEVENLABS_ASR_MODEL_ID
    else:
        error = "unsupported_primary_provider"

    meta["asr_used"] = True
    meta["asr_provider"] = primary
    meta["asr_text_len"] = len(transcript or "")

    if _is_valid_transcript(transcript, min_chars):
        return transcript, meta, "ok"

    primary_reason = error or ("short_transcript" if transcript else "empty_transcript")

    fallback_available = fallback and fallback != primary
    if fallback == "elevenlabs" and not ELEVENLABS_API_KEY:
        fallback_available = False
        if not error:
            error = "fallback_missing_key"

    if fallback_available:
        logger.info(
            "ASR primary failed; trying fallback",
            extra={
                "context": {
                    "primary": primary,
                    "fallback": fallback,
                    "status": primary_reason,
                    "min_chars": min_chars,
                    "text_len": len(transcript or ""),
                }
            },
        )
        meta["asr_fallback_used"] = True
        transcript = None
        if fallback == "openai_whisper":
            openai_model = model or "whisper-1"
            transcript, error = _transcribe_with_openai(
                audio_bytes=audio_bytes,
                filename=filename,
                mime_type=mime_type,
                model=openai_model,
                language=language,
                timeout_seconds=timeout,
            )
            meta["asr_model"] = openai_model
        elif fallback == "elevenlabs":
            transcript, error = _transcribe_with_elevenlabs(
                audio_bytes=audio_bytes,
                filename=filename,
                mime_type=mime_type,
                language=language,
                timeout_seconds=timeout,
            )
            meta["asr_model"] = ELEVENLABS_ASR_MODEL_ID
        else:
            error = "unsupported_fallback_provider"

        meta["asr_provider"] = fallback
        meta["asr_text_len"] = len(transcript or "")
        if _is_valid_transcript(transcript, min_chars):
            return transcript, meta, "ok_fallback"

    meta["asr_failed"] = True
    status = error or primary_reason
    return None, meta, status


def get_system_prompt(db: Session, client_id: UUID) -> Optional[str]:
    """Get system prompt for client."""
    logger.debug(f"Looking for prompt with client_id={client_id}")
    prompt = (
        db.query(Prompt)
        .filter(Prompt.client_id == client_id, Prompt.name == "system", Prompt.is_active == True)
        .first()
    )

    if not prompt:
        prompt = (
            db.query(Prompt)
            .filter(Prompt.client_id == client_id, Prompt.name == "system_prompt", Prompt.is_active == True)
            .first()
        )

    if prompt:
        logger.debug(f"Found prompt: {prompt.text[:100]}...")
    else:
        logger.warning(f"No prompt found for client_id={client_id}")

    return prompt.text if prompt else None


def get_conversation_history(db: Session, conversation_id: UUID, limit: int = MAX_HISTORY_MESSAGES) -> List[dict]:
    """Get recent conversation history."""
    if limit <= 0:
        return []
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )

    # Reverse to get chronological order
    messages = list(reversed(messages))

    history = []
    for msg in messages:
        role = _map_history_role(getattr(msg, "role", None))
        if role is None:
            continue
        history.append({"role": role, "content": msg.content})

    if not history:
        return history
    if not _is_env_enabled(HIERARCHICAL_MEMORY_ENABLED, default=True):
        return history
    if HIERARCHICAL_MEMORY_SUMMARY_MESSAGES <= 0:
        return history
    oldest_recent = messages[0] if messages else None
    oldest_recent_at = getattr(oldest_recent, "created_at", None)
    if oldest_recent_at is None:
        return history
    older_messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.created_at < oldest_recent_at,
        )
        .order_by(Message.created_at.desc())
        .limit(HIERARCHICAL_MEMORY_SUMMARY_MESSAGES)
        .all()
    )
    if not older_messages:
        return history
    older_messages = list(reversed(older_messages))
    summary = _build_compact_history_summary(older_messages)
    if summary:
        history.insert(0, {"role": "assistant", "content": f"[memory_summary] {summary}"})
    return history


def _build_compact_history_summary(messages: List[Message]) -> str:
    summary_lines: list[str] = []
    max_lines = max(1, HIERARCHICAL_MEMORY_SUMMARY_MAX_LINES)
    for msg in messages:
        role = _map_history_role(getattr(msg, "role", None))
        if role is None:
            continue
        content = _trim_text(str(getattr(msg, "content", "") or "").strip(), 120)
        if not content:
            continue
        role_prefix = "A" if role == "assistant" else "U"
        summary_lines.append(f"{role_prefix}: {content}")
    if not summary_lines:
        return ""
    compact = " | ".join(summary_lines[-max_lines:])
    return _trim_text(compact, HIERARCHICAL_MEMORY_SUMMARY_MAX_CHARS)


def _map_history_role(value: str | None) -> str | None:
    role = str(value or "").strip().casefold()
    if not role or role == "system":
        return None
    if role in {"assistant", "manager"}:
        return "assistant"
    return "user"


def normalize_for_matching(text: str) -> str:
    """Normalize text for matching short phrases (casefold + trim punctuation)."""
    if not text:
        return ""

    normalized = text.strip().casefold()
    normalized = re.sub(r"\[lc:[^\]]+\]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    # Make matching robust: "ок?" -> "ок", "салам!" -> "салам"
    normalized = re.sub(r"^[^\w]+|[^\w]+$", "", normalized)
    if not normalized:
        return ""
    # Collapse repeated characters to make short-phrase matching typo-tolerant.
    normalized = re.sub(r"(.)\1{1,}", r"\1", normalized)
    return normalized


def rewrite_for_service_match(
    text: str,
    client_slug: str,
    *,
    client_config: dict | None = None,
    timing_context: dict | None = None,
) -> str | None:
    normalized = normalize_for_matching(text)
    if not normalized or len(normalized) < 3:
        return None
    if not _current_openai_api_key():
        logger.warning("Service rewrite skipped: OPENAI_API_KEY missing")
        return None
    if not _should_attempt_llm(
        timing_context,
        timeout_seconds=SERVICE_REWRITE_TIMEOUT_SECONDS,
        stage="service_rewrite_llm",
    ):
        return None

    budget_meta = consume_llm_budget(
        client_slug=client_slug,
        client_config=client_config,
        scope="service_rewrite",
    )
    _append_llm_budget_event(timing_context, budget_meta)
    if not budget_meta.get("allowed", True):
        return None

    system_prompt = (
        "Ты переписываешь текст клиента в короткий запрос для поиска услуги салона. "
        "Не придумывай факты и услуги. Верни ТОЛЬКО JSON вида "
        '{"intent":"service_question|other","query":"..."}.\n'
        'intent=service_question если вопрос про услуги/цены/наличие. '
        "Если не про услуги — intent=other и query пустая строка.\n"
        "query — 1-6 слов, только суть услуги (без лишних слов).\n"
        "Примеры:\n"
        '"манник?" -> {"intent":"service_question","query":"маникюр"}\n'
        '"делаете массаж ног?" -> {"intent":"service_question","query":"массаж ног"}\n'
        '"какая погода?" -> {"intent":"other","query":""}'
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text},
    ]

    llm = get_llm_provider()
    temperature = 1.0 if FAST_MODEL.strip().lower().startswith("gpt-5") else 0.0
    llm_start = time.monotonic()
    try:
        response = llm.generate(
            messages,
            temperature=temperature,
            max_tokens=SERVICE_REWRITE_MAX_TOKENS,
            model=FAST_MODEL,
            timeout_seconds=SERVICE_REWRITE_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        _log_timing(
            "service_rewrite_llm_ms",
            (time.monotonic() - llm_start) * 1000,
            extra={
                "model_name": FAST_MODEL,
                "model_tier": "fast",
                "timeout": True,
                "timeout_seconds": SERVICE_REWRITE_TIMEOUT_SECONDS,
                "client_slug": client_slug,
            },
        )
        logger.warning(f"Service rewrite timeout after {SERVICE_REWRITE_TIMEOUT_SECONDS}s: {exc}")
        return None

    _log_timing(
        "service_rewrite_llm_ms",
        (time.monotonic() - llm_start) * 1000,
        extra={
            "model_name": FAST_MODEL,
            "model_tier": "fast",
            "timeout": False,
            "client_slug": client_slug,
        },
    )
    content = (response.content or "").strip()
    if not content:
        return None

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
        return None
    intent = payload.get("intent")
    query = payload.get("query")
    if not isinstance(intent, str):
        return None
    if intent.strip().casefold() != "service_question":
        return None
    if not isinstance(query, str):
        return None
    query = re.sub(r"\s+", " ", query).strip()
    if not query or len(query) < 2:
        return None
    return query


def rewrite_query_for_retrieval(
    text: str,
    client_slug: str | None = None,
    *,
    client_config: dict | None = None,
    timing_context: dict | None = None,
) -> dict:
    normalized = normalize_for_matching(text)
    if not normalized or len(normalized) < 3:
        return {"rewrite_used": False, "rewrite_text": "", "reason": "too_short"}
    if not _current_openai_api_key():
        logger.warning("RAG rewrite skipped: OPENAI_API_KEY missing")
        return {"rewrite_used": False, "rewrite_text": "", "reason": "missing_api_key"}
    if not _should_attempt_llm(
        timing_context,
        timeout_seconds=RAG_REWRITE_TIMEOUT_SECONDS,
        stage="rag_rewrite_llm",
    ):
        return {"rewrite_used": False, "rewrite_text": "", "reason": "deadline_exceeded"}

    budget_meta = consume_llm_budget(
        client_slug=client_slug or "unknown",
        client_config=client_config,
        scope="rag_rewrite",
    )
    _append_llm_budget_event(timing_context, budget_meta)
    if not budget_meta.get("allowed", True):
        return {"rewrite_used": False, "rewrite_text": "", "reason": "budget_exceeded"}

    system_prompt = (
        "Ты переписываешь запрос клиента для поиска по базе знаний. "
        "Исправляй сленг, опечатки, ASR-ошибки и сокращения, "
        "но не добавляй новые факты. "
        "Верни ТОЛЬКО JSON вида {\"rewrite\":\"...\",\"rewrite_used\":true/false}.\n"
        "rewrite_used=true только если текст реально улучшен.\n"
        "rewrite — 2-12 слов, сохраняй язык (RU/KZ), не добавляй цены/адреса/наличие.\n"
        "Примеры:\n"
        "\"чо по адресу\" -> {\"rewrite\":\"адрес салона\",\"rewrite_used\":true}\n"
        "\"делаете манник\" -> {\"rewrite\":\"делаете маникюр\",\"rewrite_used\":true}\n"
        "\"скок стоит педик\" -> {\"rewrite\":\"сколько стоит педикюр\",\"rewrite_used\":true}\n"
        "\"какая погода\" -> {\"rewrite\":\"какая погода\",\"rewrite_used\":false}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text},
    ]

    llm = get_llm_provider()
    temperature = 1.0 if FAST_MODEL.strip().lower().startswith("gpt-5") else 0.0
    llm_start = time.monotonic()
    try:
        response = llm.generate(
            messages,
            temperature=temperature,
            max_tokens=RAG_REWRITE_MAX_TOKENS,
            model=FAST_MODEL,
            timeout_seconds=RAG_REWRITE_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        _log_timing(
            "rag_rewrite_llm_ms",
            (time.monotonic() - llm_start) * 1000,
            extra={
                "model_name": FAST_MODEL,
                "model_tier": "fast",
                "timeout": True,
                "timeout_seconds": RAG_REWRITE_TIMEOUT_SECONDS,
                "client_slug": client_slug,
            },
        )
        logger.warning(f"RAG rewrite timeout after {RAG_REWRITE_TIMEOUT_SECONDS}s: {exc}")
        return {"rewrite_used": False, "rewrite_text": "", "reason": "timeout"}

    _log_timing(
        "rag_rewrite_llm_ms",
        (time.monotonic() - llm_start) * 1000,
        extra={
            "model_name": FAST_MODEL,
            "model_tier": "fast",
            "timeout": False,
            "client_slug": client_slug,
        },
    )

    content = (response.content or "").strip()
    if not content:
        return {"rewrite_used": False, "rewrite_text": "", "reason": "empty"}

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
        return {"rewrite_used": False, "rewrite_text": "", "reason": "invalid_json"}

    rewrite_text = payload.get("rewrite")
    rewrite_used = payload.get("rewrite_used") is True
    if not isinstance(rewrite_text, str):
        rewrite_text = ""
    rewrite_text = re.sub(r"\s+", " ", rewrite_text).strip()
    if not rewrite_text or len(rewrite_text) < 2:
        return {"rewrite_used": False, "rewrite_text": "", "reason": "too_short"}

    if normalize_for_matching(rewrite_text) == normalized:
        return {"rewrite_used": False, "rewrite_text": "", "reason": "unchanged"}

    if not rewrite_used:
        return {"rewrite_used": False, "rewrite_text": "", "reason": "model_skipped"}

    return {"rewrite_used": True, "rewrite_text": rewrite_text, "reason": "rewritten"}


def detect_multi_intent(
    text: str,
    client_slug: str | None = None,
    timing_context: dict | None = None,
    reserve_ms: float = 0.0,
) -> dict | None:
    def _clean_service_query(value: str | None) -> str:
        if not isinstance(value, str):
            return ""
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            return ""
        tokens = cleaned.split()
        if len(tokens) > 6:
            cleaned = " ".join(tokens[:6])
        if len(cleaned) < 2:
            return ""
        return cleaned

    def _clean_consult_text(value: str | None, max_words: int) -> str:
        if not isinstance(value, str):
            return ""
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            return ""
        tokens = cleaned.split()
        if len(tokens) > max_words:
            cleaned = " ".join(tokens[:max_words])
        if len(cleaned) < 2:
            return ""
        return cleaned

    consult_intent_cues = get_system_lexicon_list("consult_intent_cues")
    consult_intent_blockers = get_system_lexicon_list("consult_intent_blockers")

    def _should_force_consult_intent(raw_text: str, intents: list[str]) -> bool:
        if intents and {"booking"} & set(intents):
            return False
        normalized = normalize_for_matching(raw_text)
        if not normalized:
            return False
        if any(keyword in normalized for keyword in consult_intent_blockers):
            return False
        return any(keyword in normalized for keyword in consult_intent_cues)

    def _fallback_payload(*, timeout_safe: bool = False) -> dict:
        if timeout_safe:
            return {
                "multi_intent": False,
                "primary_intent": "other",
                "secondary_intents": [],
                "intents": ["other"],
                "service_query": "",
                "consult_intent": False,
                "consult_topic": "",
                "consult_question": "",
            }
        normalized = normalize_for_matching(text)
        intents: list[str] = []

        booking_keywords = get_system_lexicon_list("booking_keywords")
        if any(keyword in normalized for keyword in booking_keywords):
            intents.append("booking")
        relative_day_keywords = get_system_lexicon_list("booking_relative_day_keywords")
        if relative_day_keywords and any(
            re.search(rf"\b{re.escape(term)}\b", normalized) for term in relative_day_keywords
        ) and re.search(r"\b\d{1,2}\b", normalized):
            intents.append("booking")

        hours_keywords = get_system_lexicon_list("hours_keywords")
        if any(keyword in normalized for keyword in hours_keywords):
            intents.append("hours")

        price_keywords = get_system_lexicon_list("price_keywords")
        if any(keyword in normalized for keyword in price_keywords):
            intents.append("pricing")

        duration_keywords = get_system_lexicon_list("duration_keywords")
        if any(keyword in normalized for keyword in duration_keywords):
            intents.append("duration")

        location_keywords = get_system_lexicon_list("location_keywords")
        if any(keyword in normalized for keyword in location_keywords):
            intents.append("location")

        if not intents:
            intents = ["other"]
        else:
            intents = list(dict.fromkeys(intents))

        primary_intent = intents[0]
        secondary_intents = [intent for intent in intents[1:] if intent != primary_intent]
        consult_intent = _should_force_consult_intent(text, intents)
        consult_topic = _clean_consult_text(text, max_words=4) if consult_intent else ""
        consult_question = _clean_consult_text(text, max_words=12) if consult_intent else ""
        return {
            "multi_intent": len(intents) > 1,
            "primary_intent": primary_intent,
            "secondary_intents": secondary_intents,
            "intents": intents,
            "service_query": "",
            "consult_intent": consult_intent,
            "consult_topic": consult_topic,
            "consult_question": consult_question,
        }

    normalized = (text or "").strip()
    if not normalized:
        return _fallback_payload()
    if len(normalized) < 3:
        return _fallback_payload()
    if not _current_openai_api_key():
        logger.warning("Multi-intent detection skipped: OPENAI_API_KEY missing")
        return _fallback_payload()
    reserve_ms_value = 0.0
    if isinstance(reserve_ms, (int, float)):
        reserve_ms_value = max(float(reserve_ms), 0.0)
    if reserve_ms_value:
        remaining_ms = _remaining_pipeline_budget_ms(timing_context)
        if remaining_ms is not None:
            required_ms = max(float(MULTI_INTENT_TIMEOUT_SECONDS) * 1000, 0.0)
            if remaining_ms < required_ms + reserve_ms_value:
                _record_pipeline_budget_skip(
                    timing_context=timing_context,
                    stage="multi_intent_llm",
                    required_ms=required_ms + reserve_ms_value,
                    remaining_ms=remaining_ms,
                )
                if isinstance(timing_context, dict) and not timing_context.get("llm_degradation_reason"):
                    timing_context["llm_degradation_reason"] = "controller_reserved"
                return _fallback_payload()
    if not _should_attempt_llm(
        timing_context,
        timeout_seconds=MULTI_INTENT_TIMEOUT_SECONDS,
        stage="multi_intent_llm",
    ):
        return _fallback_payload()

    system_prompt = (
        "Разложи сообщение клиента на интенты. Верни ТОЛЬКО JSON строго вида "
        '{"multi_intent":true/false,"primary_intent":"booking|pricing|duration|location|hours|other",'
        '"secondary_intents":["..."],"intents":["..."],"service_query":"...",'
        '"consult_intent":true/false,"consult_topic":"...","consult_question":"..."}.\n'
        "Допустимые интенты: booking (запись/перенос/отмена/окошко), pricing (цены/стоимость), "
        "duration (длительность/время процедуры), location (адрес/как добраться), "
        "hours (график/время работы), other (другое).\n"
        "booking добавляй только если есть явная просьба записать/перенести/отменить запись. "
        "intents — уникальный список всех интентов. "
        "multi_intent=true если есть 2+ разных интента. primary_intent — главный/первый. "
        "secondary_intents — уникальные, без primary.\n"
        "service_query: 1-6 слов, ТОЛЬКО из текста клиента, коротко суть услуги. "
        "Если в сообщении есть услуга (особенно при pricing/duration/booking) — service_query обязателен, "
        "даже если есть другие интенты. Если услуги нет — пустая строка.\n"
        "consult_intent=true если клиент просит совет/рекомендацию/подбор/уход "
        "в рамках салона и НЕ спрашивает цену/адрес/наличие/запись. "
        "consult_topic — 1-4 слова, коротко тема запроса. "
        "consult_question — короткая формулировка вопроса клиента (до 12 слов).\n"
        "Если не уверен в интенте — other."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text},
    ]

    llm = get_llm_provider()
    temperature = 1.0 if FAST_MODEL.strip().lower().startswith("gpt-5") else 0.0
    retry_on_timeout = _is_env_enabled(MULTI_INTENT_RETRY_ON_TIMEOUT, default=True)
    retry_timeout_seconds = _resolve_multi_intent_retry_timeout(MULTI_INTENT_TIMEOUT_SECONDS)
    timeout_attempts: list[float] = [MULTI_INTENT_TIMEOUT_SECONDS]
    if retry_on_timeout and retry_timeout_seconds > MULTI_INTENT_TIMEOUT_SECONDS:
        timeout_attempts.append(retry_timeout_seconds)

    response = None
    for attempt_idx, timeout_seconds in enumerate(timeout_attempts):
        if (
            attempt_idx > 0
            and not _should_attempt_llm(
                timing_context,
                timeout_seconds=timeout_seconds,
                stage="multi_intent_llm_retry",
            )
        ):
            return _fallback_payload(timeout_safe=True)
        llm_start = time.monotonic()
        try:
            response = llm.generate(
                messages,
                temperature=temperature,
                max_tokens=MULTI_INTENT_MAX_TOKENS,
                model=FAST_MODEL,
                timeout_seconds=timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            _log_timing(
                "multi_intent_llm_ms",
                (time.monotonic() - llm_start) * 1000,
                timing_context=timing_context,
                extra={
                    "model_name": FAST_MODEL,
                    "model_tier": "fast",
                    "timeout": True,
                    "timeout_seconds": timeout_seconds,
                    "attempt": attempt_idx + 1,
                },
            )
            logger.warning(f"Multi-intent timeout after {timeout_seconds}s: {exc}")
            if attempt_idx + 1 < len(timeout_attempts):
                logger.warning(
                    f"Retrying multi-intent with timeout {timeout_attempts[attempt_idx + 1]}s"
                )
                continue
            return _fallback_payload(timeout_safe=True)
        except Exception as exc:
            _log_timing(
                "multi_intent_llm_ms",
                (time.monotonic() - llm_start) * 1000,
                timing_context=timing_context,
                extra={
                    "model_name": FAST_MODEL,
                    "model_tier": "fast",
                    "timeout": False,
                    "attempt": attempt_idx + 1,
                    "error": str(exc),
                },
            )
            logger.warning(f"Multi-intent failed: {exc}")
            return _fallback_payload(timeout_safe=True)

        _log_timing(
            "multi_intent_llm_ms",
            (time.monotonic() - llm_start) * 1000,
            timing_context=timing_context,
            extra={
                "model_name": FAST_MODEL,
                "model_tier": "fast",
                "timeout": False,
                "timeout_seconds": timeout_seconds,
                "attempt": attempt_idx + 1,
            },
        )
        break

    if response is None:
        return _fallback_payload(timeout_safe=True)

    content = (response.content or "").strip()
    if not content:
        return _fallback_payload()

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
        return _fallback_payload()

    allowed = {"booking", "pricing", "duration", "location", "hours", "other"}
    multi_intent_raw = payload.get("multi_intent")
    primary_intent_raw = payload.get("primary_intent")
    secondary_intents_raw = payload.get("secondary_intents", [])
    intents_raw = payload.get("intents", [])
    service_query_raw = payload.get("service_query")
    consult_intent_raw = payload.get("consult_intent")
    consult_topic_raw = payload.get("consult_topic")
    consult_question_raw = payload.get("consult_question")

    cleaned_intents: list[str] = []
    if isinstance(intents_raw, list):
        for item in intents_raw:
            if not isinstance(item, str):
                continue
            intent = item.strip().casefold()
            if intent in allowed and intent not in cleaned_intents:
                cleaned_intents.append(intent)

    primary_intent = None
    if isinstance(primary_intent_raw, str):
        primary_intent = primary_intent_raw.strip().casefold()
        if primary_intent not in allowed:
            primary_intent = "other"
    if not primary_intent:
        primary_intent = cleaned_intents[0] if cleaned_intents else "other"

    cleaned_secondary: list[str] = []
    if isinstance(secondary_intents_raw, list):
        for item in secondary_intents_raw:
            if not isinstance(item, str):
                continue
            intent = item.strip().casefold()
            if intent in allowed and intent != primary_intent and intent not in cleaned_secondary:
                cleaned_secondary.append(intent)

    if not cleaned_intents:
        cleaned_intents = [primary_intent] if primary_intent else ["other"]
    elif primary_intent and primary_intent not in cleaned_intents:
        cleaned_intents.insert(0, primary_intent)

    if not cleaned_secondary:
        cleaned_secondary = [intent for intent in cleaned_intents if intent != primary_intent]

    if isinstance(multi_intent_raw, bool):
        multi_intent = multi_intent_raw
    else:
        multi_intent = len(cleaned_intents) > 1

    service_query = _clean_service_query(service_query_raw if isinstance(service_query_raw, str) else None)
    if not service_query and {"pricing", "duration", "booking"} & set(cleaned_intents):
        rewrite_query = rewrite_for_service_match(
            text,
            client_slug or "unknown",
            timing_context=timing_context,
        )
        service_query = _clean_service_query(rewrite_query)

    consult_intent = consult_intent_raw is True
    if not consult_intent and _should_force_consult_intent(text, cleaned_intents):
        consult_intent = True
    consult_topic = _clean_consult_text(consult_topic_raw if isinstance(consult_topic_raw, str) else None, max_words=4)
    consult_question = _clean_consult_text(
        consult_question_raw if isinstance(consult_question_raw, str) else None, max_words=12
    )
    if consult_intent:
        if not consult_question:
            consult_question = _clean_consult_text(text, max_words=12)
        if not consult_topic:
            consult_topic = "general"
    else:
        consult_topic = ""
        consult_question = ""

    return {
        "multi_intent": multi_intent,
        "primary_intent": primary_intent,
        "secondary_intents": cleaned_secondary,
        "intents": cleaned_intents,
        "service_query": service_query,
        "consult_intent": consult_intent,
        "consult_topic": consult_topic,
        "consult_question": consult_question,
    }


def _build_consult_topic_payload(
    topics: list[ConsultTopic],
    candidates: list[dict] | None,
) -> list[dict]:
    topic_map = {topic.id: topic for topic in topics}
    ordered_ids: list[str] = []
    if isinstance(candidates, list):
        for item in candidates:
            topic_id = item.get("topic_id") if isinstance(item, dict) else None
            if isinstance(topic_id, str) and topic_id in topic_map and topic_id not in ordered_ids:
                ordered_ids.append(topic_id)
    if not ordered_ids:
        ordered_ids = [topic.id for topic in topics]
    payload: list[dict] = []
    for topic_id in ordered_ids:
        topic = topic_map.get(topic_id)
        if not topic:
            continue
        entry = {
            "id": topic.id,
            "title": topic.title,
            "summary": topic.summary,
            "risk_tags": topic.risk_tags,
        }
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, dict) and item.get("topic_id") == topic_id:
                    score = item.get("score")
                    if isinstance(score, (int, float)):
                        entry["score"] = round(float(score), 4)
                    break
        payload.append(entry)
    return payload


def generate_consult_controller_output(
    *,
    message_text: str,
    topics: list[ConsultTopic],
    candidates: list[dict] | None = None,
    consult_question: str | None = None,
    timing_context: dict | None = None,
) -> Result[ConsultControllerOutput]:
    if not message_text or not topics:
        return Result.failure("consult_controller_missing_input", code="invalid_input")
    if not _current_openai_api_key():
        return Result.failure("consult_controller_disabled", code="llm_disabled")
    if not _should_attempt_llm(
        timing_context,
        timeout_seconds=CONSULT_CONTROLLER_TIMEOUT_SECONDS,
        stage="consult_controller_llm",
    ):
        return Result.failure("consult_controller_skipped", code="llm_skip")

    topic_payload = _build_consult_topic_payload(topics, candidates)
    if not topic_payload:
        return Result.failure("consult_controller_empty_topics", code="topics_empty")

    system_prompt = (
        "Ты выбираешь тему консультации для ответа по playbook. "
        "Верни ТОЛЬКО JSON строго вида "
        '{"intent":"consult|info|booking|handoff|out_of_domain","topic_id":"...",'
        '"confidence":0-1,"risk_class":"low|medium|high|blocked","actions":["answer|clarify|handoff"],'
        '"slots":{...},"notes":"..."}.\n'
        "Выбери topic_id ТОЛЬКО из списка кандидатов ниже. "
        "Если ни один не подходит — topic_id=\"unknown\", intent=\"out_of_domain\", "
        "actions=[\"handoff\"], confidence<=0.4.\n"
        "Если сообщение рискованное (медицинка/юридическое/оплата/безопасность) — "
        "risk_class=high или blocked и actions содержит handoff.\n"
        "Если уверен в теме — actions включает answer. Если нужен уточняющий вопрос — clarify.\n"
        "slots используй только для кратких значений из сообщения клиента."
    )
    user_payload = {
        "message": message_text,
        "consult_question": consult_question or "",
        "candidates": topic_payload,
    }
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
    ]

    llm = get_llm_provider()
    llm_start = time.monotonic()
    temperature = 1.0 if FAST_MODEL.strip().lower().startswith("gpt-5") else 0.0
    try:
        response = llm.generate(
            messages,
            temperature=temperature,
            max_tokens=CONSULT_CONTROLLER_MAX_TOKENS,
            model=FAST_MODEL,
            timeout_seconds=CONSULT_CONTROLLER_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        _log_timing(
            "consult_controller_llm_ms",
            (time.monotonic() - llm_start) * 1000,
            timing_context=timing_context,
            extra={
                "model_name": FAST_MODEL,
                "model_tier": "fast",
                "timeout": True,
                "timeout_seconds": CONSULT_CONTROLLER_TIMEOUT_SECONDS,
            },
        )
        logger.warning(f"Consult controller timeout after {CONSULT_CONTROLLER_TIMEOUT_SECONDS}s: {exc}")
        return Result.failure("consult_controller_timeout", code="timeout")
    except Exception as exc:
        _log_timing(
            "consult_controller_llm_ms",
            (time.monotonic() - llm_start) * 1000,
            timing_context=timing_context,
            extra={"model_name": FAST_MODEL, "model_tier": "fast", "timeout": False, "error": str(exc)},
        )
        logger.warning(f"Consult controller failed: {exc}")
        return Result.failure("consult_controller_failed", code="llm_failed")

    _log_timing(
        "consult_controller_llm_ms",
        (time.monotonic() - llm_start) * 1000,
        timing_context=timing_context,
        extra={"model_name": FAST_MODEL, "model_tier": "fast", "timeout": False},
    )

    content = (response.content or "").strip()
    if not content:
        return Result.failure("consult_controller_empty", code="empty_response")
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
        return Result.failure("consult_controller_invalid_json", code="invalid_json")

    model, error = validate_consult_controller_output(payload)
    if error:
        return Result.failure(error, code="invalid_schema")
    if not isinstance(model, ConsultControllerOutput):
        return Result.failure("consult_controller_invalid_schema", code="invalid_schema")
    return Result.success(model)


def is_acknowledgement_message(text: str) -> bool:
    override = _resolve_intent_signal_override(text)
    if override is not None:
        return bool(override.get("is_ack"))
    return normalize_for_matching(text) in ACKNOWLEDGEMENT_PHRASES


def is_greeting_message(text: str) -> bool:
    override = _resolve_intent_signal_override(text)
    if override is not None:
        return bool(override.get("is_greeting"))
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    if normalized in GREETING_PHRASES:
        return True
    for phrase in GREETING_PHRASES:
        prefix = f"{phrase} "
        if normalized.startswith(prefix):
            remainder = normalized[len(prefix):].strip()
            if remainder and all(token in GREETING_FILLER_TOKENS for token in remainder.split()):
                return True
    return False


def is_thanks_message(text: str) -> bool:
    override = _resolve_intent_signal_override(text)
    if override is not None:
        return bool(override.get("is_thanks"))
    if not text:
        return False
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    if normalized in THANKS_PHRASES:
        return True
    pack_phrases = get_system_lexicon_list("thanks_phrases")
    if pack_phrases:
        if normalized in pack_phrases:
            return True
        tokens = normalized.split()
        if any(token in pack_phrases for token in tokens):
            return True
        if any(" " in phrase and phrase in normalized for phrase in pack_phrases):
            return True
    tokens = normalized.split()
    if len(tokens) == 2 and tokens[0] in THANKS_PHRASES:
        if "?" in text or any(ch.isdigit() for ch in text):
            return False
        return True
    return False


def is_low_signal_message(text: str) -> bool:
    override = _resolve_intent_signal_override(text)
    if override is not None:
        return bool(override.get("is_low_signal"))
    normalized = normalize_for_matching(text)
    if not normalized:
        return True
    if is_greeting_message(text) or is_thanks_message(text):
        return False
    tokens = normalized.split()
    if tokens:
        tokens = [token for token in tokens if token not in LOW_SIGNAL_FILLER_TOKENS]
        if not tokens:
            return True
        normalized = " ".join(tokens)
    return len(normalized) <= 2


def _has_refusal_phrase(normalized: str) -> bool:
    return any(phrase in normalized for phrase in REFUSAL_PHRASES)


def detect_refusal_flags(text: str) -> dict[str, bool]:
    override = _resolve_intent_signal_override(text)
    if override is not None:
        refusal_flags = override.get("refusal_flags")
        if isinstance(refusal_flags, dict):
            return {
                "name": bool(refusal_flags.get("name")),
                "phone": bool(refusal_flags.get("phone")),
            }
    normalized = normalize_for_matching(text)
    if not normalized:
        return {"name": False, "phone": False}
    if not _has_refusal_phrase(normalized):
        return {"name": False, "phone": False}
    name_refusal = any(token in normalized for token in REFUSAL_NAME_TOKENS)
    phone_refusal = any(token in normalized for token in REFUSAL_PHONE_TOKENS)
    return {"name": name_refusal, "phone": phone_refusal}


def is_whitelisted_message(text: str) -> bool:
    """Detect simple greetings/thanks to avoid unnecessary escalations."""
    if not text:
        return False

    normalized = normalize_for_matching(text)
    return normalized in WHITELISTED_PHRASES


def _get_last_assistant_message(history: List[dict]) -> str:
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            return msg.get("content", "")
    return ""


def _is_short_confirmation(text: str) -> bool:
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    return normalized in CONFIRMATION_PHRASES


def _assistant_expects_details(text: str) -> bool:
    if not text:
        return False
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    return any(hint in normalized for hint in OPEN_QUESTION_HINTS)


def _assistant_expects_yes_no(text: str) -> bool:
    if not text:
        return False
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    if any(hint in normalized for hint in YES_NO_QUESTION_HINTS):
        return True
    return text.strip().endswith("?") and not _assistant_expects_details(text)


def classify_confirmation(text: str) -> str:
    """Classify short confirmation replies as yes/no/unknown."""
    override = _resolve_intent_signal_override(text)
    if override is not None:
        decision = override.get("confirmation_decision")
        if isinstance(decision, str):
            normalized_decision = decision.strip().casefold()
            if normalized_decision in {"yes", "no", "unknown"}:
                return normalized_decision
    normalized = normalize_for_matching(text)
    if not normalized:
        return "unknown"

    if normalized in YES_CONFIRMATION_PHRASES:
        return "yes"
    if normalized in NO_CONFIRMATION_PHRASES:
        return "no"

    if any(token in YES_CONFIRMATION_PHRASES for token in normalized.split()):
        return "yes"
    if any(phrase in normalized for phrase in NO_CONFIRMATION_PHRASES):
        return "no"

    return "unknown"


def is_bot_status_question(text: str) -> bool:
    """Detect questions like 'бот не отвечает/ты тут?' to avoid escalation."""
    override = _resolve_intent_signal_override(text)
    if override is not None:
        return bool(override.get("is_status_question"))
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    if normalized in BOT_STATUS_KEYWORDS:
        return True
    return any(keyword in normalized for keyword in BOT_STATUS_KEYWORDS)


def get_intent_signal_override() -> dict[str, object] | None:
    override = _INTENT_SIGNAL_OVERRIDE.get()
    if not isinstance(override, dict):
        return None
    return dict(override)


@contextmanager
def use_intent_signal_override(override: dict[str, object] | None) -> Iterator[None]:
    if not isinstance(override, dict):
        yield
        return

    token = _INTENT_SIGNAL_OVERRIDE.set(dict(override))
    try:
        yield
    finally:
        _INTENT_SIGNAL_OVERRIDE.reset(token)


def _resolve_intent_signal_override(text: str | None) -> dict[str, object] | None:
    override = _INTENT_SIGNAL_OVERRIDE.get()
    if not isinstance(override, dict):
        return None
    normalized = normalize_for_matching(text)
    override_text = override.get("normalized_text")
    if not isinstance(override_text, str) or override_text != normalized:
        return None
    return override


BAD_WORDS = {
    "блять",
    "бля",
    "сука",
    "нах",
    "нахуй",
    "хер",
    "пизд",
    "fuck",
    "shit",
}


def _sanitize_query_for_rag(text: str) -> str:
    """
    Remove profanity/noise that can hurt retrieval while keeping semantic parts of the query.
    """
    if not text:
        return ""

    cleaned = text
    for bad in BAD_WORDS:
        cleaned = re.sub(bad, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or text


def _resolve_rag_query(user_message: str, timing_context: dict | None) -> str:
    rewrite_meta = timing_context.get("rag_rewrite") if timing_context else None
    rewrite_text = None
    if isinstance(rewrite_meta, dict) and rewrite_meta.get("rewrite_used"):
        rewrite_text = rewrite_meta.get("rewrite_text")
    query = rewrite_text if isinstance(rewrite_text, str) and rewrite_text.strip() else user_message
    return _sanitize_query_for_rag(query)


def _extract_branch_filter(timing_context: dict | None) -> tuple[str | None, str | None]:
    if not isinstance(timing_context, dict):
        return None, None
    branch_id = timing_context.get("branch_id")
    knowledge_tag = timing_context.get("knowledge_tag")
    if not branch_id and not knowledge_tag:
        return None, None
    return branch_id, knowledge_tag


def _record_rag_trace(
    *,
    timing_context: dict | None,
    phase: str,
    retry: bool,
    query: str,
    results: list[dict],
    rag_scores: dict | None,
) -> None:
    if timing_context is None:
        return
    timing_context["rag_attempted"] = True
    trace_payload = {
        "stage": "rag_retrieve",
        "phase": phase,
        "retry": retry,
        "query": query,
        "results": len(results),
    }
    rag_filter = timing_context.get("rag_filter") if isinstance(timing_context, dict) else None
    if isinstance(rag_filter, dict):
        trace_payload["rag_filter"] = dict(rag_filter)
    if isinstance(rag_scores, dict):
        trace_payload["rag_scores"] = rag_scores
    timing_context.setdefault("rag_trace", []).append(trace_payload)
    if isinstance(rag_scores, dict):
        best_score = max((r.get("score", 0.0) for r in results), default=0.0)
        previous_best = timing_context.get("rag_best_score", 0.0)
        if best_score >= previous_best:
            timing_context["rag_best_score"] = best_score
            timing_context["rag_scores"] = rag_scores


def _is_context_dependent_message(text: str) -> bool:
    """
    Detect short follow-up replies that often require previous context.

    Examples: "классический", "классический интересует", "аппаратный"
    """
    if not text:
        return False

    # If the user asks a question explicitly, treat it as standalone.
    if "?" in text:
        return False

    normalized = normalize_for_matching(text)
    if not normalized:
        return False

    # Very short and compact messages are likely answers/clarifications.
    if len(normalized) > 40:
        return False

    if len(normalized.split()) > 4:
        return False

    return True


def _build_contextual_search_query(history: List[dict], user_message: str) -> str:
    """Build a better RAG query for short follow-up answers by adding recent user context."""
    user_texts = [m.get("content", "") for m in history if m.get("role") == "user"]

    if not user_texts or user_texts[-1] != user_message:
        user_texts.append(user_message)

    # Take a small window of recent user messages.
    window = user_texts[-5:]

    cleaned: list[str] = []
    for text in window:
        if not text:
            continue
        # Skip pure acknowledgements/noise that don't help retrieval.
        if is_acknowledgement_message(text) or is_low_signal_message(text):
            continue
        cleaned.append(text.strip())

    query = " ".join(cleaned).strip()
    if not query:
        return user_message

    # Keep query bounded to avoid oversized embeddings and accidental topic drift.
    return query[:300]


def get_rag_confidence(
    *,
    db: Session,
    conversation_id: UUID,
    client_slug: str,
    user_message: str,
    timing_context: dict | None = None,
) -> tuple[bool, float]:
    """Return whether RAG has a confident match and its max score."""
    if not user_message:
        return False, 0.0

    max_score = 0.0
    results: list[dict] = []

    query_for_rag = _resolve_rag_query(user_message, timing_context)
    branch_id, knowledge_tag = _extract_branch_filter(timing_context)
    if not _should_attempt_stage(
        timing_context,
        required_ms=RAG_SEARCH_MIN_BUDGET_MS,
        stage="rag_search",
    ):
        return False, 0.0
    try:
        rag_start = time.monotonic()
        with _start_rag_span(timing_context, client_slug=client_slug, branch_id=branch_id):
            vector_results = search_knowledge(
                query_for_rag,
                client_slug,
                limit=3,
                branch_id=branch_id,
                knowledge_tag=knowledge_tag,
                trace_context=timing_context,
            )
        from app.services.intent_service import hybrid_retrieve_knowledge

        results, rag_scores = hybrid_retrieve_knowledge(
            query=query_for_rag,
            client_slug=client_slug,
            vector_results=vector_results,
            limit=3,
            branch_id=branch_id,
            knowledge_tag=knowledge_tag,
        )
        _log_timing(
            "rag_ms",
            (time.monotonic() - rag_start) * 1000,
            timing_context=timing_context,
            extra={
                "phase": "confidence",
                "retry": False,
                "query_len": len(query_for_rag),
                "results": len(results),
            },
        )
        _record_rag_trace(
            timing_context=timing_context,
            phase="confidence",
            retry=False,
            query=query_for_rag,
            results=results,
            rag_scores=rag_scores if isinstance(rag_scores, dict) else None,
        )
        if results:
            max_score = max(r.get("score", 0.0) for r in results)
    except Exception as exc:
        logger.warning(f"RAG confidence check failed: {exc}")

    if not results or max_score < MID_CONFIDENCE_THRESHOLD:
        if is_low_signal_message(user_message) or _is_context_dependent_message(user_message):
            history = get_conversation_history(db, conversation_id, limit=MAX_HISTORY_MESSAGES)
            contextual_query = _build_contextual_search_query(history, user_message)
            if contextual_query and contextual_query != user_message:
                contextual_query = _sanitize_query_for_rag(contextual_query)
                try:
                    if not _should_attempt_stage(
                        timing_context,
                        required_ms=RAG_SEARCH_MIN_BUDGET_MS,
                        stage="rag_search_retry",
                    ):
                        return False, max_score
                    rag_start = time.monotonic()
                    with _start_rag_span(timing_context, client_slug=client_slug, branch_id=branch_id):
                        vector_results = search_knowledge(
                            contextual_query,
                            client_slug,
                            limit=3,
                            branch_id=branch_id,
                            knowledge_tag=knowledge_tag,
                            trace_context=timing_context,
                        )
                    from app.services.intent_service import hybrid_retrieve_knowledge

                    retry_results, rag_scores = hybrid_retrieve_knowledge(
                        query=contextual_query,
                        client_slug=client_slug,
                        vector_results=vector_results,
                        limit=3,
                        branch_id=branch_id,
                        knowledge_tag=knowledge_tag,
                    )
                    _log_timing(
                        "rag_ms",
                        (time.monotonic() - rag_start) * 1000,
                        timing_context=timing_context,
                        extra={
                            "phase": "confidence",
                            "retry": True,
                            "query_len": len(contextual_query),
                            "results": len(retry_results),
                        },
                    )
                    _record_rag_trace(
                        timing_context=timing_context,
                        phase="confidence",
                        retry=True,
                        query=contextual_query,
                        results=retry_results,
                        rag_scores=rag_scores if isinstance(rag_scores, dict) else None,
                    )
                    if retry_results:
                        retry_score = max(r.get("score", 0.0) for r in retry_results)
                        if retry_score > max_score:
                            max_score = retry_score
                except Exception as exc:
                    logger.warning(f"RAG retry confidence check failed: {exc}")

    return max_score >= MID_CONFIDENCE_THRESHOLD, max_score


def generate_ai_response(
    db: Session,
    client_id: UUID,
    client_slug: str,
    conversation_id: UUID,
    user_message: str,
    append_user_message: bool = True,
    pending_hint: bool = False,
    timing_context: dict | None = None,
) -> Result[Tuple[Optional[str], str]]:
    """
    Generate AI response using LLM with knowledge base.

    Returns Result with tuple:
    - (response_text, "high") — уверенный ответ
    - (response_text, "medium") — ответ с умеренной уверенностью
    - (None, "low_confidence") — нужна эскалация
    """
    if is_greeting_message(user_message):
        return Result.success((GREETING_RESPONSE, "medium"))

    if is_thanks_message(user_message):
        return Result.success((THANKS_RESPONSE, "medium"))

    if is_acknowledgement_message(user_message):
        return Result.success((ACKNOWLEDGEMENT_RESPONSE, "medium"))

    if is_bot_status_question(user_message):
        return Result.success((BOT_STATUS_RESPONSE, "medium"))

    followup_confirmation = False
    history: List[dict] | None = None
    if is_low_signal_message(user_message):
        if _is_short_confirmation(user_message):
            history = get_conversation_history(db, conversation_id, limit=10)
            last_assistant = _get_last_assistant_message(history)
            if last_assistant and _assistant_expects_yes_no(last_assistant):
                followup_confirmation = True
            else:
                return Result.success((LOW_SIGNAL_RESPONSE, "medium"))
        else:
            return Result.success((LOW_SIGNAL_RESPONSE, "medium"))

    if not _simulation_llm_allowed(timing_context):
        if timing_context is not None:
            timing_context["llm_degradation_reason"] = "llm_skip"
        return Result.success((None, "low_confidence"))

    logger.info(f"generate_ai_response: client_id={client_id}, client_slug={client_slug}")
    if timing_context is not None:
        timing_context.setdefault("llm_cache_hit", False)
        timing_context.setdefault("llm_used", False)
        timing_context.setdefault("llm_timeout", False)

    try:
        # 1. Get system prompt
        system_prompt = get_system_prompt(db, client_id)
        if not system_prompt:
            system_prompt = "Ты полезный ассистент. Отвечай кратко и по делу."

        # 2. Search knowledge base
        knowledge_results = []
        max_score = 0.0
        if not _should_attempt_stage(
            timing_context,
            required_ms=RAG_SEARCH_MIN_BUDGET_MS,
            stage="rag_search",
        ):
            return Result.success((None, "low_confidence"))
        query_for_rag = _resolve_rag_query(user_message, timing_context)
        branch_id, knowledge_tag = _extract_branch_filter(timing_context)

        try:
            rag_start = time.monotonic()
            with _start_rag_span(timing_context, client_slug=client_slug, branch_id=branch_id):
                vector_results = search_knowledge(
                    query_for_rag,
                    client_slug,
                    limit=3,
                    branch_id=branch_id,
                    knowledge_tag=knowledge_tag,
                    trace_context=timing_context,
                )
            from app.services.intent_service import hybrid_retrieve_knowledge

            knowledge_results, rag_scores = hybrid_retrieve_knowledge(
                query=query_for_rag,
                client_slug=client_slug,
                vector_results=vector_results,
                limit=3,
                branch_id=branch_id,
                knowledge_tag=knowledge_tag,
            )
            _log_timing(
                "rag_ms",
                (time.monotonic() - rag_start) * 1000,
                timing_context=timing_context,
                extra={
                    "phase": "generate",
                    "retry": False,
                    "query_len": len(query_for_rag),
                    "results": len(knowledge_results),
                },
            )
            _record_rag_trace(
                timing_context=timing_context,
                phase="generate",
                retry=False,
                query=query_for_rag,
                results=knowledge_results,
                rag_scores=rag_scores if isinstance(rag_scores, dict) else None,
            )
            if knowledge_results:
                max_score = max(r.get("score", 0) for r in knowledge_results)
        except Exception as e:
            logger.warning(f"Knowledge search error: {e}")

        whitelisted = is_whitelisted_message(user_message)

        # 2.1 If query is a short follow-up and knowledge is weak, retry RAG with recent context.
        if not whitelisted and (not knowledge_results or max_score < MID_CONFIDENCE_THRESHOLD):
            if followup_confirmation or _is_context_dependent_message(user_message):
                history_for_query = history or get_conversation_history(
                    db, conversation_id, limit=MAX_HISTORY_MESSAGES
                )
                contextual_query = _build_contextual_search_query(history_for_query, user_message)

                if contextual_query and contextual_query != user_message:
                    contextual_query = _sanitize_query_for_rag(contextual_query)
                    try:
                        if not _should_attempt_stage(
                            timing_context,
                            required_ms=RAG_SEARCH_MIN_BUDGET_MS,
                            stage="rag_search_retry",
                        ):
                            return Result.success((None, "low_confidence"))
                        rag_start = time.monotonic()
                        with _start_rag_span(timing_context, client_slug=client_slug, branch_id=branch_id):
                            vector_results = search_knowledge(
                                contextual_query,
                                client_slug,
                                limit=3,
                                branch_id=branch_id,
                                knowledge_tag=knowledge_tag,
                                trace_context=timing_context,
                            )
                        from app.services.intent_service import hybrid_retrieve_knowledge

                        retry_results, rag_scores = hybrid_retrieve_knowledge(
                            query=contextual_query,
                            client_slug=client_slug,
                            vector_results=vector_results,
                            limit=3,
                            branch_id=branch_id,
                            knowledge_tag=knowledge_tag,
                        )
                        _log_timing(
                            "rag_ms",
                            (time.monotonic() - rag_start) * 1000,
                            timing_context=timing_context,
                            extra={
                                "phase": "generate",
                                "retry": True,
                                "query_len": len(contextual_query),
                                "results": len(retry_results),
                            },
                        )
                        _record_rag_trace(
                            timing_context=timing_context,
                            phase="generate",
                            retry=True,
                            query=contextual_query,
                            results=retry_results,
                            rag_scores=rag_scores if isinstance(rag_scores, dict) else None,
                        )
                        if retry_results:
                            retry_score = max(r.get("score", 0) for r in retry_results)
                            if retry_score > max_score:
                                knowledge_results = retry_results
                                max_score = retry_score
                            logger.info(
                                "RAG retry improved score: "
                                f"max_score={max_score:.3f} (query_len={len(contextual_query)})"
                            )
                    except Exception as e:
                        logger.warning(f"Knowledge retry error: {e}")

        # 3. Check knowledge confidence
        knowledge_context = ""
        confidence_level = "high"

        if knowledge_results and max_score >= MID_CONFIDENCE_THRESHOLD:
            confidence_level = "high" if max_score >= HIGH_CONFIDENCE_THRESHOLD else "medium"
            logger.info(
                f"Knowledge confidence: max_score={max_score:.3f}, thresholds=({MID_CONFIDENCE_THRESHOLD},{HIGH_CONFIDENCE_THRESHOLD}), level={confidence_level}"
            )
            knowledge_context = format_knowledge_context(knowledge_results)
            knowledge_context = _trim_text(knowledge_context, MAX_KNOWLEDGE_CHARS)
        else:
            logger.info(
                f"Low confidence (max_score={max_score:.3f}, threshold={MID_CONFIDENCE_THRESHOLD}), whitelisted={whitelisted}"
            )
            if not whitelisted:
                if timing_context is not None:
                    timing_context["llm_degradation_reason"] = "llm_skip"
                return Result.success((None, "low_confidence"))
            confidence_level = "medium"

        cached_response, cached_confidence = _read_llm_cache(user_message, client_slug)
        if cached_response:
            if timing_context is not None:
                timing_context["llm_cache_hit"] = True
                timing_context["llm_used"] = False
            _log_timing(
                "llm_cache_ms",
                0.0,
                timing_context=timing_context,
                extra={"cache": "hit"},
            )
            return Result.success((cached_response, cached_confidence or confidence_level))

        budget_config = _resolve_client_config(db, client_id, timing_context)
        budget_meta = consume_llm_budget(
            client_slug=client_slug,
            client_config=budget_config,
            scope="response",
        )
        _append_llm_budget_event(timing_context, budget_meta)
        if not budget_meta.get("allowed", True):
            if timing_context is not None:
                timing_context["llm_degradation_reason"] = "budget_exceeded"
            return Result.success((None, "low_confidence"))

        model_name, model_tier = _select_generation_model(user_message, max_score)

        # 4. Build messages
        messages = []

        # System prompt with knowledge context
        full_system = system_prompt
        if pending_hint:
            full_system = f"{full_system}\n\n{PENDING_SYSTEM_HINT}"
        if knowledge_context:
            full_system += f"\n\n{knowledge_context}"

        messages.append({"role": "system", "content": full_system})

        # 5. Add conversation history (last 10 messages for context)
        history = history or get_conversation_history(db, conversation_id, limit=MAX_HISTORY_MESSAGES)
        messages.extend(history)

        # 6. Add current user message (if not already in history)
        if append_user_message or not history:
            if not history or history[-1].get("content") != user_message:
                messages.append({"role": "user", "content": user_message})

        # 7. Generate response
        try:
            llm = get_llm_provider()
        except RuntimeError as exc:
            if "OPENAI_API_KEY missing" in str(exc):
                if timing_context is not None:
                    timing_context.setdefault("llm_degradation_reason", "llm_skip")
                logger.warning("AI generation skipped: OPENAI_API_KEY missing")
                return Result.success((None, "low_confidence"))
            raise
        logger.debug(f"Calling LLM with {len(messages)} messages")
        llm_start = time.monotonic()
        retry_on_timeout = _is_env_enabled(LLM_RETRY_ON_TIMEOUT, default=True)
        retry_on_transient = _is_env_enabled(LLM_RETRY_ON_TRANSIENT, default=True)
        retry_timeout_seconds = _resolve_generation_retry_timeout(LLM_TIMEOUT_SECONDS)
        timeout_attempts: list[float] = [LLM_TIMEOUT_SECONDS]
        if retry_on_timeout and retry_timeout_seconds not in timeout_attempts:
            timeout_attempts.append(retry_timeout_seconds)
        if retry_on_transient and len(timeout_attempts) == 1:
            timeout_attempts.append(timeout_attempts[0])
        fallback_model = (LLM_TIMEOUT_FALLBACK_MODEL or "").strip()
        if not fallback_model:
            fallback_model = FAST_MODEL
        if fallback_model.casefold() == model_name.casefold():
            fallback_model = ""

        if timing_context is not None:
            timing_context["llm_used"] = True

        response = None
        last_error: str | None = None
        attempt_count = 0
        transient_retry_used = False
        fallback_model_attempted = False
        timeout_seconds_used = LLM_TIMEOUT_SECONDS
        model_name_used = model_name
        for attempt_idx, timeout_seconds in enumerate(timeout_attempts):
            timeout_seconds_used = timeout_seconds
            if attempt_idx > 0 and not _should_attempt_llm(
                timing_context,
                timeout_seconds=timeout_seconds,
                stage="llm_retry",
            ):
                last_error = "deadline_exceeded"
                break
            attempt_count = attempt_idx + 1
            try:
                response = llm.generate(
                    messages,
                    temperature=1.0,
                    max_tokens=LLM_MAX_TOKENS,
                    timeout_seconds=timeout_seconds,
                    model=model_name,
                )
                model_name_used = model_name
                last_error = None
                break
            except Exception as exc:
                error_code = _classify_generation_error(exc)
                last_error = error_code
                if (
                    error_code == "timeout"
                    and retry_on_timeout
                    and attempt_idx + 1 < len(timeout_attempts)
                ):
                    logger.warning(
                        "AI generation timeout; retrying",
                        extra={
                            "context": {
                                "attempt": attempt_count,
                                "retry_timeout_seconds": retry_timeout_seconds,
                            }
                        },
                    )
                    continue
                if (
                    _is_transient_generation_error(error_code)
                    and retry_on_transient
                    and not transient_retry_used
                    and attempt_idx + 1 < len(timeout_attempts)
                ):
                    transient_retry_used = True
                    logger.warning(
                        "AI generation transient error; retrying",
                        extra={"context": {"attempt": attempt_count, "error": error_code}},
                    )
                    continue
                if error_code == "exception":
                    raise
                break

        if response is None and last_error == "timeout" and fallback_model:
            if _should_attempt_llm(
                timing_context,
                timeout_seconds=retry_timeout_seconds,
                stage="llm_fallback",
            ):
                attempt_count += 1
                fallback_model_attempted = True
                timeout_seconds_used = retry_timeout_seconds
                model_name_used = fallback_model
                try:
                    response = llm.generate(
                        messages,
                        temperature=1.0,
                        max_tokens=LLM_MAX_TOKENS,
                        timeout_seconds=retry_timeout_seconds,
                        model=fallback_model,
                    )
                    last_error = None
                except Exception as exc:
                    error_code = _classify_generation_error(exc)
                    last_error = error_code
                    if error_code == "exception":
                        raise
            else:
                last_error = "deadline_exceeded"

        if response is None:
            degrade_reason = (
                "llm_timeout"
                if last_error == "timeout"
                else ("deadline_exceeded" if last_error == "deadline_exceeded" else "provider_unavailable")
            )
            if timing_context is not None:
                timing_context["llm_timeout"] = last_error == "timeout"
                timing_context["llm_degradation_reason"] = degrade_reason
            _log_timing(
                "llm_ms",
                (time.monotonic() - llm_start) * 1000,
                timing_context=timing_context,
                extra={
                    "phase": "generate",
                    "messages": len(messages),
                    "model_name": model_name_used,
                    "model_tier": model_tier,
                    "timeout": last_error == "timeout",
                    "timeout_seconds": timeout_seconds_used,
                    "attempt_count": attempt_count,
                    "retry_on_timeout": retry_on_timeout,
                    "retry_on_transient": retry_on_transient,
                    "transient_retry_used": transient_retry_used,
                    "fallback_model_attempted": fallback_model_attempted,
                    "fallback_model": fallback_model or None,
                    "error": last_error,
                },
            )
            logger.warning(f"AI generation degraded: {last_error or 'unknown_error'}")
            return Result.success((None, "low_confidence"))
        if timing_context is not None:
            timing_context["llm_timeout"] = False
        _log_timing(
            "llm_ms",
            (time.monotonic() - llm_start) * 1000,
            timing_context=timing_context,
            extra={
                "phase": "generate",
                "messages": len(messages),
                "model_name": model_name_used,
                "model_tier": model_tier,
                "timeout": False,
                "timeout_seconds": timeout_seconds_used,
                "attempt_count": attempt_count,
                "retry_on_timeout": retry_on_timeout,
                "retry_on_transient": retry_on_transient,
                "transient_retry_used": transient_retry_used,
                "fallback_model_attempted": fallback_model_attempted,
                "fallback_model": fallback_model or None,
            },
        )
        logger.debug(f"LLM response: {response.content[:100] if response.content else 'EMPTY'}...")

        if response.content:
            _write_llm_cache(user_message, client_slug, response.content, confidence_level)
        return Result.success((response.content, confidence_level))

    except Exception as e:
        if timing_context is not None:
            timing_context["llm_degradation_reason"] = "llm_skip"
        logger.error(f"AI generation error: {e}", exc_info=True)
        alert_error("AI generation failed", {"client_id": str(client_id), "error": str(e)})
        return Result.failure(str(e), "ai_error")


def generate_consult_advice(
    *,
    db: Session,
    client_id: UUID,
    client_slug: str,
    conversation_id: UUID,
    message_text: str,
    consult_topic: str | None = None,
    consult_question: str | None = None,
    client_config: dict | None = None,
    timing_context: dict | None = None,
) -> Result[Optional[str]]:
    if not message_text:
        return Result.success(None)
    if not _current_openai_api_key():
        logger.warning("Consult LLM skipped: OPENAI_API_KEY missing")
        return Result.success(None)
    if not _should_attempt_llm(
        timing_context,
        timeout_seconds=CONSULT_LLM_TIMEOUT_SECONDS,
        stage="consult_llm",
    ):
        return Result.success(None)

    budget_config = client_config or _resolve_client_config(db, client_id, timing_context)
    budget_meta = consume_llm_budget(
        client_slug=client_slug,
        client_config=budget_config,
        scope="consult",
    )
    _append_llm_budget_event(timing_context, budget_meta)
    if not budget_meta.get("allowed", True):
        if timing_context is not None:
            timing_context["llm_degradation_reason"] = "budget_exceeded"
        return Result.success(None)

    system_prompt = (
        "Ты бережный консультант салона красоты. Дай общие советы по уходу и красоте. "
        "Запрещено: утверждать, что салон оказывает услуги, упоминать цены, запись, адрес, "
        "мастеров, акции или оплату. Запрещено медицинское консультирование и диагнозы. "
        "Ответ: 1-3 коротких предложения. Пиши на языке клиента (RU/KZ, можно смешанно)."
    )
    context_lines = []
    if consult_topic:
        context_lines.append(f"Тема: {consult_topic}")
    if consult_question:
        context_lines.append(f"Вопрос: {consult_question}")
    if context_lines:
        system_prompt = f"{system_prompt}\n\n" + "\n".join(context_lines)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message_text},
    ]
    llm = get_llm_provider()
    temperature = 1.0 if FAST_MODEL.strip().lower().startswith("gpt-5") else 0.3
    llm_start = time.monotonic()
    try:
        if timing_context is not None:
            timing_context["llm_used"] = True
            timing_context["consult_llm_used"] = True
        response = llm.generate(
            messages,
            temperature=temperature,
            max_tokens=CONSULT_LLM_MAX_TOKENS,
            timeout_seconds=CONSULT_LLM_TIMEOUT_SECONDS,
            model=FAST_MODEL,
        )
    except httpx.TimeoutException as exc:
        if timing_context is not None:
            timing_context["llm_timeout"] = True
            timing_context["llm_degradation_reason"] = "llm_timeout"
        _log_timing(
            "consult_llm_ms",
            (time.monotonic() - llm_start) * 1000,
            timing_context=timing_context,
            extra={
                "model_name": FAST_MODEL,
                "model_tier": "fast",
                "timeout": True,
                "timeout_seconds": CONSULT_LLM_TIMEOUT_SECONDS,
                "conversation_id": str(conversation_id),
            },
        )
        logger.warning(f"Consult LLM timeout after {CONSULT_LLM_TIMEOUT_SECONDS}s: {exc}")
        return Result.success(None)
    except Exception as exc:
        _log_timing(
            "consult_llm_ms",
            (time.monotonic() - llm_start) * 1000,
            timing_context=timing_context,
            extra={
                "model_name": FAST_MODEL,
                "model_tier": "fast",
                "timeout": False,
                "conversation_id": str(conversation_id),
                "error": str(exc),
            },
        )
        logger.warning(f"Consult LLM failed: {exc}")
        return Result.success(None)

    if timing_context is not None:
        timing_context["llm_timeout"] = False
    _log_timing(
        "consult_llm_ms",
        (time.monotonic() - llm_start) * 1000,
        timing_context=timing_context,
        extra={
            "model_name": FAST_MODEL,
            "model_tier": "fast",
            "timeout": False,
            "conversation_id": str(conversation_id),
        },
    )

    content = (response.content or "").strip()
    filtered = _filter_consult_advice(content)
    if not filtered:
        return Result.success(None)
    return Result.success(filtered)
