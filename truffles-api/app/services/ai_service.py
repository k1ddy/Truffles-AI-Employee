import os
import re
from typing import List, Optional, Tuple
from uuid import UUID

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

# Whitelist to avoid needless escalations on common small-talk
WHITELISTED_PHRASES = [
    "привет",
    "здравствуйте",
    "добрый день",
    "добрый вечер",
    "салам",
    "салют",
    "спасибо",
    "благодарю",
    "ок",
    "окей",
    "ok",
    "okay",
]

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

ACKNOWLEDGEMENT_RESPONSE = "Ок. Если появится вопрос — напишите, я помогу."
LOW_SIGNAL_RESPONSE = "Понял. Можете уточнить, что именно вас интересует?"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Global LLM provider instance
_llm_provider = None


def get_llm_provider() -> OpenAIProvider:
    """Get or create LLM provider instance."""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = OpenAIProvider(api_key=OPENAI_API_KEY, default_model="gpt-5-mini")
    return _llm_provider


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


def get_conversation_history(db: Session, conversation_id: UUID, limit: int = 10) -> List[dict]:
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


def is_low_signal_message(text: str) -> bool:
    normalized = normalize_for_matching(text)
    if not normalized:
        return True
    return len(normalized) <= 2


def is_whitelisted_message(text: str) -> bool:
    """Detect simple greetings/thanks to avoid unnecessary escalations."""
    if not text:
        return False

    normalized = normalize_for_matching(text)
    return any(
        normalized == phrase or normalized.startswith(f"{phrase} ")
        for phrase in WHITELISTED_PHRASES
    )


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


def generate_ai_response(
    db: Session,
    client_id: UUID,
    client_slug: str,
    conversation_id: UUID,
    user_message: str,
) -> Result[Tuple[Optional[str], str]]:
    """
    Generate AI response using LLM with knowledge base.

    Returns Result with tuple:
    - (response_text, "high") — уверенный ответ
    - (response_text, "medium") — ответ с умеренной уверенностью
    - (None, "low_confidence") — нужна эскалация
    """
    if is_acknowledgement_message(user_message):
        return Result.success((ACKNOWLEDGEMENT_RESPONSE, "medium"))

    if is_low_signal_message(user_message):
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
        try:
            knowledge_results = search_knowledge(user_message, client_slug, limit=3)
            if knowledge_results:
                max_score = max(r.get("score", 0) for r in knowledge_results)
        except Exception as e:
            logger.warning(f"Knowledge search error: {e}")

        whitelisted = is_whitelisted_message(user_message)

        # 2.1 If query is a short follow-up and knowledge is weak, retry RAG with recent context.
        if not whitelisted and (not knowledge_results or max_score < MID_CONFIDENCE_THRESHOLD):
            if _is_context_dependent_message(user_message):
                history_for_query = get_conversation_history(db, conversation_id, limit=10)
                contextual_query = _build_contextual_search_query(history_for_query, user_message)

                if contextual_query and contextual_query != user_message:
                    try:
                        retry_results = search_knowledge(contextual_query, client_slug, limit=3)
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
        else:
            logger.info(
                f"Low confidence (max_score={max_score:.3f}, threshold={MID_CONFIDENCE_THRESHOLD}), whitelisted={whitelisted}"
            )
            if not whitelisted:
                return Result.success((None, "low_confidence"))
            confidence_level = "medium"

        # 4. Build messages
        messages = []

        # System prompt with knowledge context
        full_system = system_prompt
        if knowledge_context:
            full_system += f"\n\n{knowledge_context}"

        messages.append({"role": "system", "content": full_system})

        # 5. Add conversation history (last 10 messages for context)
        history = get_conversation_history(db, conversation_id, limit=10)
        messages.extend(history)

        # 6. Add current user message (if not already in history)
        if not history or history[-1].get("content") != user_message:
            messages.append({"role": "user", "content": user_message})

        # 7. Generate response
        llm = get_llm_provider()
        logger.debug(f"Calling LLM with {len(messages)} messages")
        response = llm.generate(messages, temperature=1.0, max_tokens=2000)
        logger.debug(f"LLM response: {response.content[:100] if response.content else 'EMPTY'}...")

        return Result.success((response.content, confidence_level))

    except Exception as e:
        logger.error(f"AI generation error: {e}", exc_info=True)
        alert_error("AI generation failed", {"client_id": str(client_id), "error": str(e)})
        return Result.failure(str(e), "ai_error")
