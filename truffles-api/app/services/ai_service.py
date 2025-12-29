import hashlib
import json
import os
import re
import time
from typing import List, Optional, Tuple
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Message, Prompt
from app.services.alert_service import alert_error
from app.services.knowledge_service import format_knowledge_context, search_knowledge
from app.services.llm import OpenAIProvider
from app.services.result import Result

logger = get_logger("ai_service")

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

ACKNOWLEDGEMENT_RESPONSE = "Ок. Если появится вопрос — напишите, я помогу."
LOW_SIGNAL_RESPONSE = "Понял. Можете уточнить, что именно вас интересует?"
GREETING_RESPONSE = "Здравствуйте! Чем могу помочь?"
THANKS_RESPONSE = "Рад помочь. Если нужно что-то ещё — пишите."
BOT_STATUS_RESPONSE = "Я на связи. Напишите ваш вопрос, и я помогу."
OUT_OF_DOMAIN_RESPONSE = "Я помогаю по нашим услугам, записи и ценам. Чем могу помочь?"
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
    "не надо",
    "не нужно",
    "не хочу",
    "не сейчас",
    "потом",
}

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
SERVICE_REWRITE_TIMEOUT_SECONDS = float(os.environ.get("SERVICE_REWRITE_TIMEOUT_SECONDS", "1.2"))
SERVICE_REWRITE_MAX_TOKENS = int(os.environ.get("SERVICE_REWRITE_MAX_TOKENS", "80"))
MULTI_INTENT_TIMEOUT_SECONDS = float(os.environ.get("MULTI_INTENT_TIMEOUT_SECONDS", "1.2"))
MULTI_INTENT_MAX_TOKENS = int(os.environ.get("MULTI_INTENT_MAX_TOKENS", "120"))
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
MAX_KNOWLEDGE_CHARS = int(os.environ.get("LLM_KNOWLEDGE_CHARS", "1500"))
LLM_CACHE_TTL_SECONDS = int(os.environ.get("LLM_CACHE_TTL_SECONDS", "86400"))
LLM_CACHE_PREFIX = "truffles:llm_cache"
LLM_CACHE_SOCKET_TIMEOUT_SECONDS = float(os.environ.get("LLM_CACHE_SOCKET_TIMEOUT_SECONDS", "0.3"))
REDIS_URL = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
POLICY_VERSION = os.environ.get("POLICY_VERSION", "v1")

# Global LLM provider instance
_llm_provider = None
_llm_cache_client = None
_llm_cache_url = None


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _log_timing(
    stage: str,
    elapsed_ms: float,
    *,
    timing_context: dict | None = None,
    extra: dict | None = None,
) -> None:
    context: dict = {}
    if timing_context:
        context.update(timing_context)
    if extra:
        context.update(extra)
    context["stage"] = stage
    context["elapsed_ms"] = round(elapsed_ms, 2)
    logger.info("Timing", extra={"context": context})


def get_llm_provider() -> OpenAIProvider:
    """Get or create LLM provider instance."""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = OpenAIProvider(api_key=OPENAI_API_KEY, default_model=FAST_MODEL)
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
    if not OPENAI_API_KEY:
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
    if not OPENAI_API_KEY:
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
        role = "assistant" if msg.role == "assistant" else "user"
        if msg.role == "system":
            continue  # Skip system messages
        history.append({"role": role, "content": msg.content})

    return history


def normalize_for_matching(text: str) -> str:
    """Normalize text for matching short phrases (casefold + trim punctuation)."""
    if not text:
        return ""

    normalized = text.strip().casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    # Make matching robust: "ок?" -> "ок", "салам!" -> "салам"
    normalized = re.sub(r"^[^\w]+|[^\w]+$", "", normalized)
    return normalized


def rewrite_for_service_match(text: str, client_slug: str) -> str | None:
    normalized = normalize_for_matching(text)
    if not normalized or len(normalized) < 3:
        return None
    if not OPENAI_API_KEY:
        logger.warning("Service rewrite skipped: OPENAI_API_KEY missing")
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
    llm_start = time.monotonic()
    try:
        response = llm.generate(
            messages,
            temperature=0.0,
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


def detect_multi_intent(text: str) -> dict | None:
    normalized = (text or "").strip()
    if not normalized or len(normalized) < 3:
        return None
    if not OPENAI_API_KEY:
        logger.warning("Multi-intent detection skipped: OPENAI_API_KEY missing")
        return None

    system_prompt = (
        "Разложи сообщение клиента на интенты. Верни ТОЛЬКО JSON строго вида "
        '{"multi_intent":true/false,"primary_intent":"booking|pricing|duration|location|hours|other",'
        '"secondary_intents":["..."],"intents":["..."],"service_query":"..."}.\n'
        "Допустимые интенты: booking (запись/перенос/отмена/окошко), pricing (цены/стоимость), "
        "duration (длительность/время процедуры), location (адрес/как добраться), "
        "hours (график/время работы), other (другое).\n"
        "booking добавляй только если есть явная просьба записать/перенести/отменить запись. "
        "intents — уникальный список всех интентов. "
        "multi_intent=true если есть 2+ разных интента. primary_intent — главный/первый. "
        "secondary_intents — уникальные, без primary.\n"
        "service_query: 1-6 слов, коротко суть услуги, если речь про услугу/цену/длительность/запись. "
        "Если не про услугу — пустая строка. Если не уверен — other."
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
            max_tokens=MULTI_INTENT_MAX_TOKENS,
            model=FAST_MODEL,
            timeout_seconds=MULTI_INTENT_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        _log_timing(
            "multi_intent_llm_ms",
            (time.monotonic() - llm_start) * 1000,
            extra={
                "model_name": FAST_MODEL,
                "model_tier": "fast",
                "timeout": True,
                "timeout_seconds": MULTI_INTENT_TIMEOUT_SECONDS,
            },
        )
        logger.warning(f"Multi-intent timeout after {MULTI_INTENT_TIMEOUT_SECONDS}s: {exc}")
        return None
    except Exception as exc:
        _log_timing(
            "multi_intent_llm_ms",
            (time.monotonic() - llm_start) * 1000,
            extra={"model_name": FAST_MODEL, "model_tier": "fast", "timeout": False, "error": str(exc)},
        )
        logger.warning(f"Multi-intent failed: {exc}")
        return None

    _log_timing(
        "multi_intent_llm_ms",
        (time.monotonic() - llm_start) * 1000,
        extra={"model_name": FAST_MODEL, "model_tier": "fast", "timeout": False},
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

    allowed = {"booking", "pricing", "duration", "location", "hours", "other"}
    multi_intent_raw = payload.get("multi_intent")
    primary_intent_raw = payload.get("primary_intent")
    secondary_intents_raw = payload.get("secondary_intents", [])
    intents_raw = payload.get("intents", [])
    service_query_raw = payload.get("service_query")

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

    service_query = service_query_raw if isinstance(service_query_raw, str) else ""
    service_query = re.sub(r"\s+", " ", service_query).strip()
    if service_query:
        tokens = service_query.split()
        if len(tokens) > 6:
            service_query = " ".join(tokens[:6])
    if len(service_query) < 2:
        service_query = ""

    return {
        "multi_intent": multi_intent,
        "primary_intent": primary_intent,
        "secondary_intents": cleaned_secondary,
        "intents": cleaned_intents,
        "service_query": service_query,
    }


def is_acknowledgement_message(text: str) -> bool:
    return normalize_for_matching(text) in ACKNOWLEDGEMENT_PHRASES


def is_greeting_message(text: str) -> bool:
    return normalize_for_matching(text) in GREETING_PHRASES


def is_thanks_message(text: str) -> bool:
    return normalize_for_matching(text) in THANKS_PHRASES


def is_low_signal_message(text: str) -> bool:
    normalized = normalize_for_matching(text)
    if not normalized:
        return True
    if is_greeting_message(text) or is_thanks_message(text):
        return False
    return len(normalized) <= 2


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
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    if normalized in BOT_STATUS_KEYWORDS:
        return True
    return any(keyword in normalized for keyword in BOT_STATUS_KEYWORDS)


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

    query_for_rag = _sanitize_query_for_rag(user_message)
    try:
        rag_start = time.monotonic()
        results = search_knowledge(query_for_rag, client_slug, limit=3)
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
                    rag_start = time.monotonic()
                    retry_results = search_knowledge(contextual_query, client_slug, limit=3)
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
        query_for_rag = _sanitize_query_for_rag(user_message)

        try:
            rag_start = time.monotonic()
            knowledge_results = search_knowledge(query_for_rag, client_slug, limit=3)
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
                        rag_start = time.monotonic()
                        retry_results = search_knowledge(contextual_query, client_slug, limit=3)
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
        llm = get_llm_provider()
        logger.debug(f"Calling LLM with {len(messages)} messages")
        llm_start = time.monotonic()
        try:
            if timing_context is not None:
                timing_context["llm_used"] = True
            response = llm.generate(
                messages,
                temperature=1.0,
                max_tokens=LLM_MAX_TOKENS,
                timeout_seconds=LLM_TIMEOUT_SECONDS,
                model=model_name,
            )
        except httpx.TimeoutException as exc:
            if timing_context is not None:
                timing_context["llm_timeout"] = True
            _log_timing(
                "llm_ms",
                (time.monotonic() - llm_start) * 1000,
                timing_context=timing_context,
                extra={
                    "phase": "generate",
                    "messages": len(messages),
                    "model_name": model_name,
                    "model_tier": model_tier,
                    "timeout": True,
                    "timeout_seconds": LLM_TIMEOUT_SECONDS,
                },
            )
            logger.warning(f"LLM timeout after {LLM_TIMEOUT_SECONDS}s: {exc}")
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
                "model_name": model_name,
                "model_tier": model_tier,
                "timeout": False,
            },
        )
        logger.debug(f"LLM response: {response.content[:100] if response.content else 'EMPTY'}...")

        if response.content:
            _write_llm_cache(user_message, client_slug, response.content, confidence_level)
        return Result.success((response.content, confidence_level))

    except Exception as e:
        logger.error(f"AI generation error: {e}", exc_info=True)
        alert_error("AI generation failed", {"client_id": str(client_id), "error": str(e)})
        return Result.failure(str(e), "ai_error")
