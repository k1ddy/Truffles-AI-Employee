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
    "салют",
    "дд",
}

THANKS_PHRASES = {
    "спасибо",
    "благодарю",
    "спасибо большое",
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
INTENT_TIMEOUT_SECONDS = float(os.environ.get("INTENT_TIMEOUT_SECONDS", "2"))
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "6"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "600"))
MAX_HISTORY_MESSAGES = int(os.environ.get("LLM_HISTORY_MESSAGES", "6"))
MAX_KNOWLEDGE_CHARS = int(os.environ.get("LLM_KNOWLEDGE_CHARS", "1500"))

# Global LLM provider instance
_llm_provider = None


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
        )
        cleaned = (transcript or "").strip()
        return cleaned or None
    except Exception as exc:
        logger.warning(f"Audio transcription failed: {exc}")
        return None


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
            response = llm.generate(
                messages,
                temperature=1.0,
                max_tokens=LLM_MAX_TOKENS,
                timeout_seconds=LLM_TIMEOUT_SECONDS,
                model=model_name,
            )
        except httpx.TimeoutException as exc:
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

        return Result.success((response.content, confidence_level))

    except Exception as e:
        logger.error(f"AI generation error: {e}", exc_info=True)
        alert_error("AI generation failed", {"client_id": str(client_id), "error": str(e)})
        return Result.failure(str(e), "ai_error")
