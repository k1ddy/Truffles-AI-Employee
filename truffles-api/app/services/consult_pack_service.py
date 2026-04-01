from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.schemas.consult import ConsultPlaybook, ConsultTopic, validate_consult_playbook

_KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[1] / "knowledge"


def _normalize_client_slug(client_slug: str | None) -> str:
    slug = str(client_slug or "").strip()
    return slug


def _consult_pack_path(client_slug: str | None) -> Path:
    slug = _normalize_client_slug(client_slug)
    return _KNOWLEDGE_BASE_DIR / slug / "CONSULT_PLAYBOOK.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _ensure_sentence_end(text: str, *, question: bool = False) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if cleaned.endswith((".", "!", "?")):
        return cleaned
    return f"{cleaned}?" if question else f"{cleaned}."


def _select_items(items: list[str], seed: int, limit: int) -> list[str]:
    if not items:
        return []
    if len(items) <= limit:
        return list(items)
    rng = random.Random(seed)
    return rng.sample(items, k=limit)


def _build_variant_seed(*, conversation_id: str | None, topic_id: str) -> tuple[str, int]:
    base = conversation_id or "conversation"
    digest = hashlib.sha256(f"{base}:{topic_id}".encode("utf-8")).hexdigest()
    variant_id = digest[:8]
    return variant_id, int(variant_id, 16)


def _normalize_text(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().lower().split())


def _looks_like_duration_question(normalized_question: str) -> bool:
    if not normalized_question:
        return False
    duration_tokens = (
        "сколько времени",
        "как долго",
        "долго",
        "длится",
        "занимает",
    )
    return any(token in normalized_question for token in duration_tokens)


def _looks_like_availability_question(normalized_question: str) -> bool:
    if not normalized_question:
        return False
    availability_tokens = (
        "есть ли",
        "есть",
        "делаете",
        "предоставляете",
        "бывают",
    )
    return any(token in normalized_question for token in availability_tokens)


def _prepend_distinct(sentence: str, body: str) -> str:
    clean_sentence = _ensure_sentence_end(sentence)
    clean_body = body.strip()
    if not clean_sentence:
        return clean_body
    if not clean_body:
        return clean_sentence
    body_norm = _normalize_text(clean_body)
    sentence_norm = _normalize_text(clean_sentence)
    if sentence_norm and sentence_norm in body_norm:
        return clean_body
    return f"{clean_sentence} {clean_body}".strip()


def _parse_duration_numbers(raw_value: Any, *, hours: bool) -> tuple[int, int] | None:
    if raw_value is None:
        return None
    text = str(raw_value).strip().replace(",", ".").replace("–", "-")
    if not text:
        return None
    number_matches = re.findall(r"\d+(?:\.\d+)?", text)
    if not number_matches:
        return None
    values: list[int] = []
    for token in number_matches:
        try:
            numeric = float(token)
        except ValueError:
            continue
        minutes = int(round(numeric * 60)) if hours else int(round(numeric))
        if minutes > 0:
            values.append(minutes)
    if not values:
        return None
    return min(values), max(values)


def _duration_estimate_hint(client_slug: str | None) -> str | None:
    if not client_slug:
        return None
    try:
        from app.services.pack_runtime_service import load_yaml_truth
    except Exception:
        return None
    truth = load_yaml_truth(client_slug)
    if not isinstance(truth, dict):
        return None
    estimates = truth.get("service_duration_estimates")
    if not isinstance(estimates, dict):
        return None
    mins: list[int] = []
    maxs: list[int] = []
    for key, value in estimates.items():
        key_text = str(key).strip().lower()
        hours = key_text.endswith("_час")
        parsed = _parse_duration_numbers(value, hours=hours)
        if not parsed:
            continue
        low, high = parsed
        mins.append(low)
        maxs.append(high)
    if not mins or not maxs:
        return None
    overall_min = min(mins)
    overall_max = max(maxs)
    if overall_min <= 0 or overall_max <= 0:
        return None
    if overall_min == overall_max:
        return f"По времени обычно около {overall_min} минут, зависит от услуги"
    return f"По времени обычно от {overall_min} до {overall_max} минут, зависит от услуги"


def _select_question(topic: ConsultTopic, seed: int) -> str | None:
    questions = list(topic.required_questions or [])
    if not questions:
        questions = list(topic.optional_questions or [])
    if not questions:
        return None
    if len(questions) == 1:
        return _ensure_sentence_end(questions[0], question=True)
    index = seed % len(questions)
    return _ensure_sentence_end(questions[index], question=True)


@dataclass(frozen=True)
class ConsultPackDecision:
    action: str
    response: str
    intent: str | None = None
    meta: dict[str, Any] | None = None


def get_consult_topic(
    playbook: ConsultPlaybook,
    topic_id: str,
) -> ConsultTopic | None:
    topic_key = (topic_id or "").strip()
    if not topic_key:
        return None
    for topic in playbook.topics:
        if topic.id == topic_key:
            return topic
    return None


def build_consult_pack_reply(
    *,
    playbook: ConsultPlaybook,
    topic_id: str,
    conversation_id: str | None,
    consult_question: str | None = None,
    client_slug: str | None = None,
) -> ConsultPackDecision | None:
    topic = get_consult_topic(playbook, topic_id)
    if not topic:
        return None
    variant_id, seed = _build_variant_seed(conversation_id=conversation_id, topic_id=topic.id)
    advice_items = [
        _ensure_sentence_end(item) for item in _select_items(topic.allowed_advice, seed, limit=2)
    ]
    question = _select_question(topic, seed)
    next_step = _ensure_sentence_end(topic.next_step or "") if topic.next_step else ""
    parts = [item for item in advice_items if item]
    if question:
        parts.append(question)
    if next_step:
        parts.append(next_step)
    response = " ".join(part for part in parts if part).strip()
    if not response:
        return None
    normalized_consult_question = _normalize_text(consult_question)
    question_signal = None
    if _looks_like_duration_question(normalized_consult_question):
        question_signal = "duration"
        duration_hint = _duration_estimate_hint(client_slug)
        if duration_hint:
            response = _prepend_distinct(duration_hint, response)
        else:
            response = _prepend_distinct(
                "По времени это зависит от выбранной процедуры",
                response,
            )
    elif _looks_like_availability_question(normalized_consult_question):
        question_signal = "availability"
        response = _prepend_distinct(
            "Да, такие варианты есть",
            response,
        )
    meta: dict[str, Any] = {
        "consult_intent": True,
        "consult_topic": topic.id,
        "consult_topic_id": topic.id,
        "consult_question": consult_question or "",
        "consult_playbook_id": topic.id,
        "consult_variant_id": variant_id,
        "consult_questions": [question] if question else [],
        "consult_options": advice_items,
        "tips_used": advice_items,
        "source": "pack",
    }
    if question_signal == "duration":
        meta["info_sections"] = ["duration"]
        meta["fact_intents"] = ["duration"]
    elif question_signal == "availability":
        meta["info_sections"] = ["master"]
        meta["fact_intents"] = ["master"]
    return ConsultPackDecision(
        action="reply",
        response=response,
        intent="consult_reply",
        meta=meta,
    )


def select_consult_question(
    playbook: ConsultPlaybook,
    *,
    topic_id: str,
    conversation_id: str | None,
) -> str | None:
    topic = get_consult_topic(playbook, topic_id)
    if not topic:
        return None
    _variant_id, seed = _build_variant_seed(conversation_id=conversation_id, topic_id=topic.id)
    return _select_question(topic, seed)


@lru_cache(maxsize=32)
def load_consult_playbook(
    client_slug: str | None,
) -> tuple[ConsultPlaybook | None, str | None]:
    path = _consult_pack_path(client_slug)
    if not path.exists():
        return None, "consult_playbook_missing"
    payload = _load_yaml(path)
    if not payload:
        return None, "consult_playbook_empty"
    playbook, error = validate_consult_playbook(payload)
    if error:
        return None, error
    return playbook, None
