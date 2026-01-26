from __future__ import annotations

import hashlib
import random
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
