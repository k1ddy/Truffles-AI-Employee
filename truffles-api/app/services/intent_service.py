from enum import Enum

from app.logging_config import get_logger
from app.services.ai_service import get_llm_provider

logger = get_logger("intent_service")


class Intent(str, Enum):
    HUMAN_REQUEST = "human_request"  # Клиент просит менеджера/человека
    FRUSTRATION = "frustration"  # Клиент раздражён, ругается
    REJECTION = "rejection"  # Клиент отказывается от помощи бота ("нет", "не надо")
    QUESTION = "question"  # Вопрос о продукте/услуге
    GREETING = "greeting"  # Приветствие
    THANKS = "thanks"  # Благодарность
    OTHER = "other"  # Всё остальное


ESCALATION_INTENTS = {Intent.HUMAN_REQUEST, Intent.FRUSTRATION}
REJECTION_INTENTS = {Intent.REJECTION}

CLASSIFY_PROMPT = """Классифицируй сообщение клиента. Верни ТОЛЬКО одно слово из списка:
- human_request — клиент просит человека/менеджера/оператора
- frustration — клиент раздражён, ругается, использует мат
- rejection — клиент отказывается от помощи бота (нет, не надо, не нужно, сам разберусь)
- question — вопрос о продукте, услуге, цене, доставке
- greeting — приветствие (привет, здравствуйте, добрый день)
- thanks — благодарность (спасибо, благодарю)
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

Сообщение: {message}

Ответ (одно слово):"""


def classify_intent(message: str) -> Intent:
    """Classify user message intent using LLM."""
    try:
        llm = get_llm_provider()

        prompt = CLASSIFY_PROMPT.format(message=message)
        messages = [{"role": "user", "content": prompt}]

        response = llm.generate(messages, temperature=1.0, max_tokens=100)
        result = response.content.strip().lower()

        # Parse response
        for intent in Intent:
            if intent.value in result:
                return intent

        return Intent.OTHER

    except Exception as e:
        logger.error(f"Intent classification error: {e}")
        return Intent.OTHER


def should_escalate(intent: Intent) -> bool:
    """Check if intent requires escalation to human."""
    return intent in ESCALATION_INTENTS


def is_rejection(intent: Intent) -> bool:
    """Check if client is rejecting bot's help."""
    return intent in REJECTION_INTENTS
