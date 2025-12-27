import re
import time
from enum import Enum
from typing import Any, Iterable, Tuple

import httpx

from app.logging_config import get_logger
from app.services.ai_service import (
    FAST_MODEL,
    INTENT_TIMEOUT_SECONDS,
    get_llm_provider,
    normalize_for_matching,
)

logger = get_logger("intent_service")


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


def classify_intent(message: str) -> Intent:
    """Classify user message intent using LLM."""
    try:
        if is_opt_out_message(message):
            return Intent.REJECTION

        if is_frustration_message(message):
            return Intent.FRUSTRATION

        if is_human_request_message(message):
            return Intent.HUMAN_REQUEST

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
    if any(key in client_config for key in ("anchors_in", "anchors_out", "in_threshold", "out_threshold")):
        return client_config
    return {}


def _score_against_anchors(text_normalized: str, tokens: set[str], anchors: Iterable[str]) -> tuple[float, str | None]:
    best_score = 0.0
    best_anchor = None
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
    return best_score, best_anchor


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
    in_threshold = float(config.get("in_threshold", 0.62))
    out_threshold = float(config.get("out_threshold", 0.62))
    margin = float(config.get("margin", 0.08))
    min_len = int(config.get("min_len", 5))

    text_normalized = _normalize_text(text)
    tokens = set(text_normalized.split()) if text_normalized else set()

    if len(text_normalized) < min_len or (not anchors_in and not anchors_out):
        return (
            DomainIntent.UNKNOWN,
            0.0,
            0.0,
            {
                "in_threshold": in_threshold,
                "out_threshold": out_threshold,
                "margin": margin,
                "anchors_in": len(anchors_in),
                "anchors_out": len(anchors_out),
                "message_len": len(text_normalized),
            },
        )

    in_score, matched_in = _score_against_anchors(text_normalized, tokens, anchors_in)
    out_score, matched_out = _score_against_anchors(text_normalized, tokens, anchors_out)

    domain_intent = DomainIntent.UNKNOWN
    if in_score >= in_threshold and in_score >= out_score + margin:
        domain_intent = DomainIntent.IN_DOMAIN
    elif out_score >= out_threshold and out_score >= in_score + margin:
        domain_intent = DomainIntent.OUT_OF_DOMAIN

    meta = {
        "in_threshold": in_threshold,
        "out_threshold": out_threshold,
        "margin": margin,
        "anchors_in": len(anchors_in),
        "anchors_out": len(anchors_out),
        "matched_in": matched_in,
        "matched_out": matched_out,
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

    strict_out_threshold = float(config.get("strict_out_threshold", max(out_threshold, 0.8)))
    strong_out_threshold = float(config.get("strong_out_threshold", max(out_threshold, 0.72)))
    strict_margin = float(config.get("strict_margin", 0.18))
    strong_margin = float(config.get("strong_margin", 0.12))
    strict_in_max = float(config.get("strict_in_max", 0.4))
    strong_in_max = float(config.get("strong_in_max", 0.5))
    strict_min_len = int(config.get("strict_min_len", 6))

    text_normalized = _normalize_text(text)
    message_len = len(text_normalized)

    strong = False
    if domain_intent == DomainIntent.OUT_OF_DOMAIN:
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
    }
    return strong, meta
