from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
import yaml

from app.logging_config import get_logger
from app.services.knowledge_service import get_embedding

_DEMO_SALON_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "demo_salon"
_TRUTH_PATH = _DEMO_SALON_DIR / "SALON_TRUTH.yaml"
_INTENTS_PATH = _DEMO_SALON_DIR / "INTENTS_PHRASES_DEMO_SALON.yaml"
_SERVICES_COLLECTION = "services_index"

_SERVICE_MATCH_THRESHOLD = float(os.environ.get("SERVICE_SEMANTIC_MATCH_THRESHOLD", "0.40"))
_SERVICE_SUGGEST_THRESHOLD = float(os.environ.get("SERVICE_SEMANTIC_SUGGEST_THRESHOLD", "0.25"))
_SERVICE_SUGGEST_LIMIT = int(os.environ.get("SERVICE_SEMANTIC_SUGGEST_LIMIT", "3"))
_SERVICE_QUERY_SEMANTIC_THRESHOLD = float(os.environ.get("SERVICE_QUERY_SEMANTIC_THRESHOLD", "0.72"))
_QUESTION_TYPE_THRESHOLD = float(os.environ.get("QUESTION_TYPE_SEMANTIC_THRESHOLD", "0.55"))
_QUESTION_TYPE_MARGIN = float(os.environ.get("QUESTION_TYPE_SEMANTIC_MARGIN", "0.08"))
_QDRANT_HOST = os.environ.get("QDRANT_HOST", "http://qdrant:6333")
_QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")

logger = get_logger("demo_salon_knowledge")


@dataclass(frozen=True)
class DemoSalonDecision:
    action: str
    response: str
    intent: str | None = None
    collect: list[str] | None = None
    meta: dict[str, Any] | None = None


@dataclass(frozen=True)
class SemanticServiceMatch:
    action: str
    response: str
    score: float
    canonical_name: str | None = None
    suggestions: list[str] | None = None


@dataclass(frozen=True)
class SemanticQuestionType:
    kind: str
    score: float
    second_score: float


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.casefold().replace("ё", "е")
    normalized = re.sub(r"\[.*?\]", " ", normalized)
    normalized = normalized.replace("гель-лак", "гель лак").replace("гельлак", "гель лак")
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _split_question_segments(text: str) -> list[str]:
    if not text:
        return []
    segments = [segment.strip() for segment in re.split(r"[?!\.,;]+", text) if segment.strip()]
    if segments:
        return segments
    cleaned = text.strip()
    return [cleaned] if cleaned else []


def _normalize_consult_label(value: str) -> str:
    cleaned = str(value or "").replace("_", " ").strip()
    return _normalize_text(cleaned)


def _clean_consult_value(value: Any, max_words: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return None
    tokens = cleaned.split()
    if len(tokens) > max_words:
        cleaned = " ".join(tokens[:max_words])
    return cleaned or None


@lru_cache(maxsize=4)
def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def load_yaml_truth() -> dict:
    return _load_yaml(_TRUTH_PATH)


def load_intents_phrases() -> dict:
    data = _load_yaml(_INTENTS_PATH)
    intents = data.get("demo_salon_intents") if isinstance(data, dict) else None
    return intents if isinstance(intents, dict) else {}


def _load_consult_playbooks() -> list[dict[str, Any]]:
    truth = load_yaml_truth()
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    playbooks = domain_pack.get("consult_playbooks") if isinstance(domain_pack, dict) else None
    if not isinstance(playbooks, list):
        return []
    return [item for item in playbooks if isinstance(item, dict)]


@lru_cache(maxsize=2)
def _build_phrase_index() -> dict[str, list[str]]:
    intents = load_intents_phrases()
    index: dict[str, list[str]] = {}
    for intent, phrases in intents.items():
        if isinstance(phrases, list):
            normalized = [_normalize_text(str(phrase)) for phrase in phrases if str(phrase).strip()]
            index[intent] = [p for p in normalized if p]
    return index


def phrase_match_intent(text: str) -> set[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return set()
    matches: set[str] = set()
    for intent, phrases in _build_phrase_index().items():
        for phrase in phrases:
            if not phrase:
                continue
            if len(phrase) <= 3:
                if re.search(rf"\b{re.escape(phrase)}\b", normalized):
                    matches.add(intent)
                    break
                continue
            if phrase in normalized:
                matches.add(intent)
                break
    return matches


def _flatten_offtopic_phrases() -> list[str]:
    intents = load_intents_phrases()
    offtopic = intents.get("offtopic_examples") if isinstance(intents, dict) else None
    if not isinstance(offtopic, dict):
        return []
    phrases: list[str] = []
    for group in offtopic.values():
        if isinstance(group, list):
            phrases.extend(group)
    normalized = [_normalize_text(str(item)) for item in phrases if str(item).strip()]
    return [p for p in normalized if p]


@lru_cache(maxsize=2)
def _offtopic_phrases() -> list[str]:
    return _flatten_offtopic_phrases()


def _format_money(value: Any) -> str:
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{amount:,}".replace(",", " ")


def _tokenize(text: str) -> list[str]:
    normalized = _normalize_text(text)
    return [token for token in normalized.split() if token]


_SERVICE_STOPWORDS = {
    "и",
    "или",
    "на",
    "по",
    "за",
    "до",
    "от",
    "для",
    "у",
    "в",
    "во",
    "к",
    "с",
    "со",
}

_OFFTOPIC_KEYWORDS = [
    "чат бот",
    "ботов",
    "разработк",
    "сайт",
    "crm",
    "интеграц",
    "мессенджер",
]


def _normalize_alias_tokens(text: str) -> list[str]:
    tokens = _tokenize(text)
    return [token for token in tokens if token and token not in _SERVICE_STOPWORDS]


@lru_cache(maxsize=2)
def _build_price_index() -> list[dict[str, Any]]:
    truth = load_yaml_truth()
    items: list[dict[str, Any]] = []
    for category in truth.get("price_list", []) if isinstance(truth, dict) else []:
        for item in category.get("items", []) if isinstance(category, dict) else []:
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            tokens = _tokenize(name)
            if not tokens:
                continue
            items.append(
                {
                    "name": name,
                    "tokens": tokens,
                    "item": item,
                }
            )
    return items


@lru_cache(maxsize=2)
def _build_price_name_index() -> dict[str, dict[str, Any]]:
    truth = load_yaml_truth()
    index: dict[str, dict[str, Any]] = {}
    for category in truth.get("price_list", []) if isinstance(truth, dict) else []:
        for item in category.get("items", []) if isinstance(category, dict) else []:
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            index[_normalize_text(name)] = item
    return index


@lru_cache(maxsize=2)
def _build_service_index() -> list[dict[str, Any]]:
    truth = load_yaml_truth()
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    services = catalog.get("services") if isinstance(catalog, dict) else None
    if not isinstance(services, list):
        return []

    index: list[dict[str, Any]] = []
    for service in services:
        if not isinstance(service, dict):
            continue
        name = str(service.get("name", "")).strip()
        if not name:
            continue
        aliases: list[str] = [name]
        extra_aliases = service.get("aliases")
        if isinstance(extra_aliases, list):
            aliases.extend([str(alias) for alias in extra_aliases if str(alias).strip()])

        alias_tokens: list[list[str]] = []
        for alias in aliases:
            tokens = _normalize_alias_tokens(alias)
            if tokens:
                alias_tokens.append(tokens)

        price_items = service.get("price_items")
        index.append(
            {
                "name": name,
                "aliases": alias_tokens,
                "quick_price_key": str(service.get("quick_price_key")).strip()
                if service.get("quick_price_key")
                else None,
                "price_items": [str(item) for item in price_items if str(item).strip()]
                if isinstance(price_items, list)
                else [],
                "description": str(service.get("description", "")).strip() or None,
                "duration_text": str(service.get("duration_text", "")).strip() or None,
            }
        )
    return index


@lru_cache(maxsize=2)
def _service_tokens() -> set[str]:
    tokens: set[str] = set()
    for entry in _build_service_index():
        for alias in entry.get("aliases", []):
            tokens.update(alias)
    return tokens


def _message_has_service_token(normalized: str) -> bool:
    if not normalized:
        return False
    message_tokens = normalized.split()
    for token in _service_tokens():
        if _token_matches(token, message_tokens):
            return True
    return False


def _is_offtopic_message(normalized: str) -> bool:
    if not normalized:
        return False
    if any(phrase and phrase in normalized for phrase in _offtopic_phrases()):
        return True
    return _contains_any(normalized, _OFFTOPIC_KEYWORDS)


def _match_service(normalized: str) -> dict[str, Any] | None:
    if not normalized:
        return None
    message_tokens = normalized.split()
    best = None
    best_len = 0
    for entry in _build_service_index():
        for alias_tokens in entry.get("aliases", []):
            if not alias_tokens:
                continue
            if all(_token_matches(token, message_tokens) for token in alias_tokens):
                if len(alias_tokens) > best_len:
                    best = entry
                    best_len = len(alias_tokens)
    return best


def _token_matches(token: str, message_tokens: list[str]) -> bool:
    for msg in message_tokens:
        if msg == token:
            return True
        if len(token) >= 3 and msg.startswith(token):
            return True
        if len(msg) >= 3 and token.startswith(msg):
            return True
    return False


def _find_best_price_item(message: str) -> dict[str, Any] | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None
    message_tokens = normalized.split()
    best = None
    best_len = 0
    for entry in _build_price_index():
        tokens = entry["tokens"]
        if not tokens:
            continue
        if all(_token_matches(token, message_tokens) for token in tokens):
            if len(tokens) > best_len:
                best = entry
                best_len = len(tokens)
    return best


def _contains_any(normalized: str, keywords: list[str]) -> bool:
    return any(keyword in normalized for keyword in keywords)


def _contains_word(normalized: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", normalized) is not None


def _contains_any_words(normalized: str, words: list[str]) -> bool:
    return any(_contains_word(normalized, word) for word in words)


def _collect_consult_triggers(playbook: dict[str, Any]) -> list[str]:
    raw = playbook.get("triggers")
    items: list[str] = []
    if isinstance(raw, list):
        items.extend(raw)
    elif isinstance(raw, dict):
        for key in ("ru", "kk", "any", "all"):
            values = raw.get(key)
            if isinstance(values, list):
                items.extend(values)
    aliases = playbook.get("aliases")
    if isinstance(aliases, list):
        items.extend(aliases)
    normalized = [_normalize_text(str(item)) for item in items if str(item).strip()]
    return [item for item in normalized if item]


def _consult_topic_matches(playbook: dict[str, Any], consult_topic: str) -> bool:
    if not consult_topic:
        return False
    target = _normalize_consult_label(consult_topic)
    if not target:
        return False
    for key in ("id", "topic"):
        value = playbook.get(key)
        if isinstance(value, str) and _normalize_consult_label(value) == target:
            return True
    aliases = playbook.get("aliases")
    if isinstance(aliases, list):
        for alias in aliases:
            if isinstance(alias, str) and _normalize_consult_label(alias) == target:
                return True
    return False


def _select_consult_playbook(
    message: str,
    consult_topic: str | None,
    playbooks: list[dict[str, Any]],
    *,
    allow_fallback: bool,
) -> dict[str, Any] | None:
    normalized = _normalize_text(message)
    if consult_topic:
        for playbook in playbooks:
            if _consult_topic_matches(playbook, consult_topic):
                return playbook
    if normalized:
        for playbook in playbooks:
            triggers = _collect_consult_triggers(playbook)
            if triggers and _contains_any(normalized, triggers):
                return playbook
    if allow_fallback:
        for playbook in playbooks:
            if playbook.get("fallback") is True:
                return playbook
    return None


def _ensure_question_mark(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if cleaned.endswith("?"):
        return cleaned
    return f"{cleaned}?"


def _format_consult_reply(playbook: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    lead = str(playbook.get("lead") or "").strip()
    questions_raw = playbook.get("questions")
    options_raw = playbook.get("options")

    questions_items = questions_raw if isinstance(questions_raw, list) else []
    options_items = options_raw if isinstance(options_raw, list) else []

    questions = [
        _ensure_question_mark(str(item))
        for item in questions_items
        if isinstance(item, str) and item.strip()
    ]
    options = [
        str(item).strip()
        for item in options_items
        if isinstance(item, str) and item.strip()
    ]

    selected_questions = [q for q in questions if q][:2]
    selected_options = [opt for opt in options if opt][:3]

    lines: list[str] = []
    if lead:
        lines.append(lead)
    if selected_questions:
        lines.append(" ".join(selected_questions))
    if selected_options:
        lines.append("Можно рассмотреть варианты:")
        lines.extend([f"- {option}" for option in selected_options])

    reply = "\n".join(line for line in lines if line)
    return reply, selected_questions, selected_options


def _should_skip_consult(normalized: str, raw_text: str | None = None) -> bool:
    if not normalized:
        return True
    if _has_price_signal(normalized, raw_text):
        return True
    if _has_duration_signal(normalized, raw_text):
        return True
    if _looks_like_hours_question(normalized):
        return True
    if _contains_any(normalized, ["адрес", "где вы", "как добрат", "как доехать", "как пройти", "остановк"]):
        return True
    return False


def _looks_like_hours_question(normalized: str) -> bool:
    if not normalized:
        return False
    if _contains_any(
        normalized,
        [
            "график",
            "до скольки",
            "открыты",
            "открыто",
            "часы",
            "часов",
            "время работы",
            "во сколько",
            "открывает",
            "открываете",
            "открываетесь",
            "в будни",
            "по будням",
            "в выходные",
            "по выходным",
        ],
    ):
        return True
    if "работаете" in normalized:
        return True
    if "работает" in normalized and _contains_any(normalized, ["вы", "салон"]):
        if _contains_any(normalized, ["сегодня", "сейчас", "открыт", "будни", "выходн"]):
            return True
    return False


def _has_price_signal(normalized: str, raw_text: str | None = None) -> bool:
    price_keywords = ["цена", "прайс", "стоим", "стоимость", "почем", "ценник", "скок", "скока"]
    currency_words = ["тг", "тенге", "руб", "рубл", "usd", "eur", "доллар", "евро"]
    if _contains_any(normalized, price_keywords):
        return True
    if "сколько" in normalized and "стоит" in normalized:
        return True
    if _contains_any(normalized, currency_words):
        return True
    if raw_text and re.search(r"[₸$€₽]", raw_text):
        return True
    return False


def _has_duration_signal(normalized: str, raw_text: str | None = None) -> bool:
    if not normalized:
        return False
    duration_keywords = [
        "длится",
        "длительность",
        "сколько по времени",
        "по времени",
        "сколько времени",
        "сколько занимает",
        "как долго",
        "время процедуры",
    ]
    if _contains_any(normalized, duration_keywords):
        return True
    if re.search(r"\bзанимает\b", normalized):
        return True
    if "сколько" in normalized and "времени" in normalized:
        return True
    if raw_text:
        if _extract_minutes(raw_text) is not None:
            return True
        if re.search(r"\b(\d{1,2})\s*(?:час|часа|часов|ч)\b", raw_text, flags=re.IGNORECASE):
            return True
    return False


def _extract_minutes(text: str) -> int | None:
    match = re.search(r"\b(\d{1,3})\s*(?:мин|минут|м)\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _format_price_reply(item: dict[str, Any]) -> str:
    name = item.get("name", "Услуга")
    if "price" in item:
        price = _format_money(item.get("price"))
        return f"{name} — {price} ₸."
    if "price_from" in item:
        price = _format_money(item.get("price_from"))
        return f"{name} — от {price} ₸."
    return f"{name} — уточните цену у администратора."


def _format_service_price_items(item_names: list[str]) -> str | None:
    if not item_names:
        return None
    index = _build_price_name_index()
    replies: list[str] = []
    for name in item_names:
        item = index.get(_normalize_text(name))
        if item:
            replies.append(_format_price_reply(item))
    if replies:
        return " ".join(replies)
    return None


def _format_service_reply(service: dict[str, Any], truth: dict) -> str | None:
    quick_key = service.get("quick_price_key")
    if quick_key:
        quick_answer = truth.get("price_quick_answers", {}).get(quick_key)
        if quick_answer:
            return quick_answer
    price_items = service.get("price_items") if isinstance(service, dict) else None
    reply = _format_service_price_items(price_items or [])
    if reply:
        return reply
    description = service.get("description") if isinstance(service, dict) else None
    if description:
        return description
    return None


def _format_service_not_found_reply() -> str | None:
    truth = load_yaml_truth()
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    template = None
    suggestions: list[str] = []
    if isinstance(catalog, dict):
        template = catalog.get("not_found_reply")
        suggestion_items = catalog.get("suggestions")
        if isinstance(suggestion_items, list):
            suggestions = [str(item) for item in suggestion_items if str(item).strip()]
    if not template:
        template = "В списке услуг нет такой позиции. Могу уточнить или предложить: {suggestions}."
    suggestions_text = ", ".join(suggestions)
    if "{suggestions}" in template:
        return template.format(suggestions=suggestions_text)
    if suggestions_text:
        return f"{template} {suggestions_text}."
    return template


def _format_service_suggestions_reply(suggestions: list[str]) -> str | None:
    truth = load_yaml_truth()
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    template = None
    if isinstance(catalog, dict):
        template = catalog.get("not_found_reply")
    if not template:
        template = "В списке услуг нет такой позиции. Возможно, вы имели в виду: {suggestions}."
    suggestions_text = ", ".join(suggestions)
    if "{suggestions}" in template:
        return template.format(suggestions=suggestions_text)
    if suggestions_text:
        return f"{template} {suggestions_text}."
    return template


@lru_cache(maxsize=2)
def _question_type_examples() -> dict[str, list[str]]:
    truth = load_yaml_truth()
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    typical = domain_pack.get("typical_questions") if isinstance(domain_pack, dict) else None
    if not isinstance(typical, dict):
        return {}

    examples: dict[str, list[str]] = {}
    for kind in ("pricing", "duration", "hours"):
        phrases: list[str] = []
        block = typical.get(kind)
        if isinstance(block, dict):
            for items in block.values():
                if isinstance(items, list):
                    for phrase in items:
                        text = str(phrase).strip()
                        if text:
                            phrases.append(text)
        elif isinstance(block, list):
            for phrase in block:
                text = str(phrase).strip()
                if text:
                    phrases.append(text)
        examples[kind] = phrases
    return examples


def _coerce_embedding(raw: Any) -> list[float] | None:
    if not isinstance(raw, list) or not raw:
        return None
    try:
        return [float(value) for value in raw]
    except (TypeError, ValueError):
        return None


def _local_text_embedding(text: str, dim: int = 64) -> list[float]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    grams: list[str] = []
    if len(normalized) >= 3:
        for index in range(len(normalized) - 2):
            grams.append(normalized[index : index + 3])
    else:
        grams.append(normalized)
    vector = [0.0] * dim
    for gram in grams:
        digest = hashlib.sha256(gram.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


@lru_cache(maxsize=4)
def _question_type_embeddings(use_fallback: bool) -> dict[str, list[list[float]]]:
    examples = _question_type_examples()
    embeddings: dict[str, list[list[float]]] = {}
    for kind, phrases in examples.items():
        vectors: list[list[float]] = []
        for phrase in phrases:
            vector: list[float] | None = None
            if use_fallback:
                vector = _local_text_embedding(phrase)
            else:
                try:
                    vector = _coerce_embedding(get_embedding(phrase))
                except Exception:
                    vector = None
            if vector:
                vectors.append(vector)
        if vectors:
            embeddings[kind] = vectors
    return embeddings


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if not vector_a or not vector_b:
        return 0.0
    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_question_type(
    text: str,
    *,
    include_kinds: set[str] | None = None,
    return_multi: bool = False,
) -> SemanticQuestionType | list[SemanticQuestionType] | None:
    normalized = _normalize_text(text)
    if not normalized or len(normalized) < 3:
        return [] if return_multi else None

    if include_kinds is None:
        include_kinds = {"pricing", "duration"}

    query_vector = None
    use_fallback = False
    error_detail = None
    try:
        query_vector = _coerce_embedding(get_embedding(text))
    except Exception as exc:
        error_detail = str(exc)
        query_vector = None
    if not query_vector:
        use_fallback = True
        query_vector = _local_text_embedding(text)
        logger.warning(
            "question_type fallback to local embedding",
            extra={"context": {"error": error_detail or "embedding_unavailable"}},
        )

    examples = _question_type_embeddings(use_fallback)
    if not examples and not use_fallback:
        use_fallback = True
        query_vector = _local_text_embedding(text)
        examples = _question_type_embeddings(True)
        logger.warning(
            "question_type fallback to local embedding",
            extra={"context": {"error": "no_examples_with_bge"}},
        )
    if not examples:
        return None

    scores: dict[str, float] = {}
    for kind, vectors in examples.items():
        if kind not in include_kinds:
            continue
        best = 0.0
        for vector in vectors:
            score = _cosine_similarity(query_vector, vector)
            if score > best:
                best = score
        scores[kind] = best

    if not scores:
        return [] if return_multi else None

    def _pick_types(score_map: dict[str, float]) -> list[SemanticQuestionType]:
        if not score_map:
            return []
        sorted_scores = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
        top_kind, top_score = sorted_scores[0]
        second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0
        if top_score < _QUESTION_TYPE_THRESHOLD:
            return []
        if return_multi:
            if len(sorted_scores) > 1 and (top_score - second_score) <= _QUESTION_TYPE_MARGIN:
                picked = sorted_scores[:2]
            else:
                picked = sorted_scores[:1]
        else:
            if (top_score - second_score) >= _QUESTION_TYPE_MARGIN:
                picked = sorted_scores[:1]
            else:
                return []
        return [
            SemanticQuestionType(kind=kind, score=score, second_score=second_score) for kind, score in picked
        ]

    picked = _pick_types(scores)
    if picked:
        return picked if return_multi else picked[0]

    if not use_fallback:
        fallback_vector = _local_text_embedding(text)
        fallback_examples = _question_type_embeddings(True)
        fallback_scores: dict[str, float] = {}
        for kind, vectors in fallback_examples.items():
            if kind not in include_kinds:
                continue
            best = 0.0
            for vector in vectors:
                score = _cosine_similarity(fallback_vector, vector)
                if score > best:
                    best = score
            fallback_scores[kind] = best
        picked_fallback = _pick_types(fallback_scores)
        if return_multi:
            return picked_fallback
        return picked_fallback[0] if picked_fallback else None

    return [] if return_multi else None


def _format_service_duration_reply(service: dict[str, Any] | None) -> str:
    truth = load_yaml_truth()
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    if service:
        duration_text = service.get("duration_text") if isinstance(service, dict) else None
        if isinstance(duration_text, str) and duration_text.strip():
            duration_text = duration_text.strip()
            name = service.get("name") or "Услуга"
            suffix = "" if duration_text.endswith((".", "!", "?")) else "."
            return f"{name} — {duration_text}{suffix}"

    if isinstance(catalog, dict):
        clarify = catalog.get("duration_clarify")
        if isinstance(clarify, str) and clarify.strip():
            return clarify.strip()

    return "По времени зависит от услуги. Какая именно?"


def _select_presence_service_name(message: str, candidates: list[str]) -> str | None:
    if not message or not candidates:
        return None
    query_vector = _local_text_embedding(message)
    if not query_vector:
        return None
    best_name = None
    best_score = 0.0
    for candidate in candidates:
        service = _find_catalog_service_by_name(candidate)
        if not service:
            continue
        name = service.get("name") if isinstance(service, dict) else None
        if not isinstance(name, str) or not name.strip():
            continue
        score = _cosine_similarity(query_vector, _local_text_embedding(name))
        if score > best_score:
            best_score = score
            best_name = name.strip()
    return best_name


def _format_service_presence_reply(message: str, match: SemanticServiceMatch | None) -> str | None:
    if not message or not match:
        return None
    candidates: list[str] = []
    seen: set[str] = set()
    if isinstance(match.canonical_name, str) and match.canonical_name.strip():
        cleaned = match.canonical_name.strip()
        candidates.append(cleaned)
        seen.add(cleaned)
    if isinstance(match.suggestions, list):
        for suggestion in match.suggestions:
            if isinstance(suggestion, str):
                cleaned = suggestion.strip()
                if cleaned and cleaned not in seen:
                    candidates.append(cleaned)
                    seen.add(cleaned)
    service_name = _select_presence_service_name(message, candidates)
    if not service_name:
        return None
    truth = load_yaml_truth()
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    template = catalog.get("service_presence_reply") if isinstance(catalog, dict) else None
    if not isinstance(template, str) or not template.strip():
        return None
    template = template.strip()
    if "{service}" in template:
        return template.format(service=service_name)
    return f"{template} {service_name}."


def _format_service_presence_reply_for_name(service_name: str) -> str | None:
    if not isinstance(service_name, str) or not service_name.strip():
        return None
    truth = load_yaml_truth()
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    template = catalog.get("service_presence_reply") if isinstance(catalog, dict) else None
    if not isinstance(template, str) or not template.strip():
        return None
    template = template.strip()
    cleaned = service_name.strip()
    if "{service}" in template:
        return template.format(service=cleaned)
    return f"{template} {cleaned}."


def _find_catalog_service_by_name(name: str) -> dict[str, Any] | None:
    if not name:
        return None
    needle = _normalize_text(name)
    for entry in _build_service_index():
        if _normalize_text(entry.get("name") or "") == needle:
            return entry
    return None


def _format_semantic_service_reply(payload: dict) -> str | None:
    canonical_name = payload.get("canonical_name") if isinstance(payload, dict) else None
    if isinstance(canonical_name, str) and canonical_name.strip():
        service = _find_catalog_service_by_name(canonical_name)
        if service:
            reply = _format_service_reply(service, load_yaml_truth())
            if reply:
                return reply
        price_item = _build_price_name_index().get(_normalize_text(canonical_name))
        if price_item:
            return _format_price_reply(price_item)

    price_item_payload = payload.get("price_item") if isinstance(payload, dict) else None
    if isinstance(price_item_payload, dict):
        return _format_price_reply(price_item_payload)
    return None


def _should_attempt_semantic_match(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return len(normalized) >= 3


def _search_services_index(text: str, client_slug: str, limit: int) -> list[dict[str, Any]]:
    if not text or not client_slug:
        return []
    try:
        embedding = get_embedding(text)
    except Exception as exc:
        logger.warning("services_index embedding failed", extra={"context": {"error": str(exc)}})
        return []

    headers = {}
    if _QDRANT_API_KEY:
        headers["api-key"] = _QDRANT_API_KEY

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{_QDRANT_HOST}/collections/{_SERVICES_COLLECTION}/points/search",
                headers=headers,
                json={
                    "vector": embedding,
                    "limit": limit,
                    "score_threshold": 0.0,
                    "filter": {"must": [{"key": "client_slug", "match": {"value": client_slug}}]},
                    "with_payload": True,
                },
            )
    except Exception as exc:
        logger.warning("services_index search failed", extra={"context": {"error": str(exc)}})
        return []

    if response.status_code == 404:
        return []
    if response.status_code != 200:
        logger.warning(
            "services_index search failed",
            extra={"context": {"status": response.status_code, "body": response.text[:200]}},
        )
        return []

    data = response.json()
    results: list[dict[str, Any]] = []
    for point in data.get("result", []):
        payload = point.get("payload") if isinstance(point, dict) else None
        if not isinstance(payload, dict):
            continue
        results.append(
            {
                "score": float(point.get("score") or 0.0),
                "payload": payload,
            }
        )
    return results


def semantic_service_match(text: str, client_slug: str) -> SemanticServiceMatch | None:
    if not _should_attempt_semantic_match(text):
        return None
    results = _search_services_index(text, client_slug, _SERVICE_SUGGEST_LIMIT)
    if not results:
        return None

    top = results[0]
    score = float(top.get("score") or 0.0)
    normalized = _normalize_text(text)
    raw_text = text or ""
    if len(normalized.split()) <= 2 and "?" not in raw_text and score < 0.55:
        return None
    payload = top.get("payload") if isinstance(top.get("payload"), dict) else {}
    suggestions: list[str] = []
    for item in results:
        payload_item = item.get("payload") if isinstance(item.get("payload"), dict) else None
        name = payload_item.get("canonical_name") if isinstance(payload_item, dict) else None
        if isinstance(name, str) and name.strip():
            cleaned = name.strip()
            if cleaned not in suggestions:
                suggestions.append(cleaned)

    if score >= _SERVICE_MATCH_THRESHOLD:
        reply = _format_semantic_service_reply(payload)
        if reply:
            return SemanticServiceMatch(
                action="match",
                response=reply,
                score=score,
                canonical_name=payload.get("canonical_name"),
                suggestions=suggestions,
            )

    if score >= _SERVICE_SUGGEST_THRESHOLD:
        reply = _format_service_suggestions_reply(suggestions or [])
        if reply:
            return SemanticServiceMatch(
                action="suggest",
                response=reply,
                score=score,
                canonical_name=payload.get("canonical_name"),
                suggestions=suggestions,
            )

    return None


def _extract_intent_decomp(intent_decomp: dict | None) -> tuple[set[str], str | None]:
    if not isinstance(intent_decomp, dict):
        return set(), None
    allowed = {"booking", "pricing", "duration", "location", "hours", "other"}
    intents: list[str] = []
    raw_intents = intent_decomp.get("intents")
    if isinstance(raw_intents, list):
        for item in raw_intents:
            if not isinstance(item, str):
                continue
            intent = item.strip().casefold()
            if intent in allowed and intent not in intents:
                intents.append(intent)
    if not intents:
        primary = intent_decomp.get("primary_intent")
        if isinstance(primary, str):
            primary = primary.strip().casefold()
            if primary in allowed:
                intents.append(primary)
        secondary = intent_decomp.get("secondary_intents")
        if isinstance(secondary, list):
            for item in secondary:
                if not isinstance(item, str):
                    continue
                intent = item.strip().casefold()
                if intent in allowed and intent not in intents:
                    intents.append(intent)
    service_query = intent_decomp.get("service_query")
    if isinstance(service_query, str):
        service_query = service_query.strip()
        if not service_query:
            service_query = None
    else:
        service_query = None
    return set(intents), service_query


def _clean_service_query(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned or len(cleaned) < 2:
        return None
    tokens = cleaned.split()
    if len(tokens) > 6:
        cleaned = " ".join(tokens[:6])
    return cleaned or None


def _resolve_service_query_meta(
    message: str,
    client_slug: str | None,
    intent_decomp: dict | None,
    *,
    require_query: bool,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "service_query": None,
        "service_query_source": "none",
        "service_query_score": 0.0,
    }
    if isinstance(intent_decomp, dict):
        cleaned = _clean_service_query(intent_decomp.get("service_query"))
        if cleaned:
            source_override = intent_decomp.get("service_query_source")
            score_override = intent_decomp.get("service_query_score")
            source = "intent_decomp"
            if isinstance(source_override, str) and source_override in {"intent_decomp", "context"}:
                source = source_override
            meta["service_query"] = cleaned
            meta["service_query_source"] = source
            if isinstance(score_override, (int, float)):
                meta["service_query_score"] = float(score_override)
            else:
                meta["service_query_score"] = 1.0
            return meta
    if require_query and message and client_slug:
        match = semantic_service_match(message, client_slug)
        if match and match.action == "match" and match.score >= _SERVICE_QUERY_SEMANTIC_THRESHOLD:
            candidate = match.canonical_name
            if not candidate and match.suggestions:
                candidate = match.suggestions[0]
            cleaned = _clean_service_query(candidate)
            if cleaned:
                meta["service_query"] = cleaned
                meta["service_query_source"] = "semantic_match"
                meta["service_query_score"] = match.score
        if not meta.get("service_query"):
            fallback_service = _match_service(_normalize_text(message))
            if isinstance(fallback_service, dict):
                fallback_name = _clean_service_query(fallback_service.get("name"))
                if fallback_name:
                    meta["service_query"] = fallback_name
                    meta["service_query_source"] = "semantic_match"
                    meta["service_query_score"] = 1.0
        if not meta.get("service_query"):
            price_item = _find_best_price_item(message)
            if isinstance(price_item, dict):
                fallback_name = _clean_service_query(price_item.get("name"))
                if fallback_name:
                    meta["service_query"] = fallback_name
                    meta["service_query_source"] = "semantic_match"
                    meta["service_query_score"] = 1.0
    return meta


def _resolve_service_from_query(service_query: str | None) -> dict[str, Any] | None:
    if not service_query:
        return None
    normalized = _normalize_text(service_query)
    if not normalized:
        return None
    return _match_service(normalized)


def compose_multi_truth_reply(
    message: str,
    client_slug: str | None,
    intent_decomp: dict | None = None,
    *,
    return_meta: bool = False,
) -> str | tuple[str, dict[str, Any]] | None:
    if not message or not client_slug:
        return None
    segments = _split_question_segments(message)
    if not segments:
        return None
    replies: list[str] = []
    seen: set[str] = set()
    truth = load_yaml_truth()
    intent_kinds, service_query = _extract_intent_decomp(intent_decomp)
    intent_kinds = {kind for kind in intent_kinds if kind in {"hours", "pricing", "duration"}}
    if not intent_kinds and len(segments) < 2:
        return None
    normalized_message = _normalize_text(message)
    if intent_kinds:
        if "hours" in intent_kinds:
            hours_like = any(_looks_like_hours_question(_normalize_text(seg)) for seg in segments)
            if not hours_like:
                intent_kinds.discard("hours")
        if "pricing" in intent_kinds and not _has_price_signal(normalized_message, message):
            intent_kinds.discard("pricing")
        if "duration" in intent_kinds and not _has_duration_signal(normalized_message, message):
            intent_kinds.discard("duration")
    info_detected = bool(intent_kinds)
    needs_service_query = _has_price_signal(normalized_message, message) or _has_duration_signal(
        normalized_message, message
    )
    service_query_meta = _resolve_service_query_meta(
        message,
        client_slug,
        intent_decomp,
        require_query=needs_service_query,
    )
    service_query = service_query_meta.get("service_query")
    service_match_from_query = None
    service_from_query = None
    fallback_service_name_from_query = None
    if service_query:
        service_match_from_query = semantic_service_match(service_query, client_slug)
        service_from_query = _resolve_service_from_query(service_query)
        if isinstance(service_from_query, dict):
            name = service_from_query.get("name")
            if isinstance(name, str) and name.strip():
                fallback_service_name_from_query = name.strip()
    for segment in segments:
        normalized_segment = _normalize_text(segment)
        if not normalized_segment:
            continue
        question_types = semantic_question_type(
            segment,
            include_kinds={"hours", "pricing", "duration"},
            return_multi=True,
        )
        if question_types is None:
            question_types = []
        elif not isinstance(question_types, list):
            question_types = [question_types]
        kinds = {
            question.kind
            for question in question_types
            if hasattr(question, "kind") and isinstance(getattr(question, "kind"), str)
        }
        if intent_kinds:
            kinds |= intent_kinds
        if "hours" in kinds and not _looks_like_hours_question(normalized_segment):
            kinds.discard("hours")
        if "pricing" in kinds and not _has_price_signal(normalized_segment, segment):
            kinds.discard("pricing")
        if "duration" in kinds and not _has_duration_signal(normalized_segment, segment):
            kinds.discard("duration")
        service_match = semantic_service_match(segment, client_slug)
        fallback_service = _match_service(normalized_segment) if not service_match else None
        fallback_service_name = None
        if isinstance(fallback_service, dict):
            name = fallback_service.get("name")
            if isinstance(name, str) and name.strip():
                fallback_service_name = name.strip()
        if not fallback_service_name and fallback_service_name_from_query:
            fallback_service_name = fallback_service_name_from_query
        if kinds:
            info_detected = True

        def _add_reply(text: str | None) -> None:
            if not text:
                return
            cleaned = text.strip()
            if not cleaned or cleaned in seen:
                return
            replies.append(cleaned)
            seen.add(cleaned)

        if "hours" in kinds:
            _add_reply(format_reply_from_truth("hours"))
        if len(replies) >= 2:
            break
        if "pricing" in kinds:
            if not service_query:
                _add_reply(format_reply_from_truth("service_clarify"))
            elif service_match_from_query and service_match_from_query.action == "match":
                _add_reply(service_match_from_query.response)
            else:
                fallback_reply = None
                if isinstance(service_from_query, dict):
                    fallback_reply = _format_service_reply(service_from_query, truth)
                if fallback_reply:
                    _add_reply(fallback_reply)
                else:
                    _add_reply(format_reply_from_truth("service_clarify"))
        if len(replies) >= 2:
            break
        if "duration" in kinds:
            if not service_query:
                _add_reply(_format_service_duration_reply(None))
            else:
                _add_reply(_format_service_duration_reply(service_from_query))
        if len(replies) >= 2:
            break
        if (
            not needs_service_query
            and service_match
            and service_match.action == "match"
            and not {"pricing", "duration"} & kinds
        ):
            _add_reply(_format_service_presence_reply(segment, service_match))
        elif not needs_service_query and fallback_service_name and not {"pricing", "duration"} & kinds:
            _add_reply(_format_service_presence_reply_for_name(fallback_service_name))
        if len(replies) >= 2:
            break

    if not info_detected or len(replies) < 2:
        return None
    reply = "\n\n".join(replies[:2])
    if return_meta:
        return reply, service_query_meta
    return reply


def _looks_like_service_question(normalized: str, raw_text: str | None = None) -> bool:
    if not normalized:
        return False
    if not _message_has_service_token(normalized):
        return False
    if _has_price_signal(normalized, raw_text):
        return True
    service_keywords = ["делаете", "есть ли", "есть", "оказываете", "предоставляете"]
    if _contains_any(normalized, service_keywords):
        return True
    return False


def _format_promotions(truth: dict, intent: str | None = None) -> str:
    promotions = truth.get("promotions") if isinstance(truth, dict) else {}
    items = promotions.get("items") if isinstance(promotions, dict) else []
    if not isinstance(items, list):
        items = []

    if intent == "promotion_first_visit":
        for promo in items:
            if "перв" in str(promo.get("name", "")).casefold():
                return (
                    f"На первое посещение действует скидка {promo.get('discount_percent')}% "
                    "на услуги. Скидки не суммируются."
                )
    if intent == "promotion_birthday":
        for promo in items:
            if "именин" in str(promo.get("name", "")).casefold():
                return (
                    f"Именинникам скидка {promo.get('discount_percent')}% — "
                    "7 дней до/после даты рождения при документе."
                )
    if intent == "promotion_student":
        for promo in items:
            if "студент" in str(promo.get("name", "")).casefold() or "пенсион" in str(promo.get("name", "")).casefold():
                return (
                    f"Студентам/пенсионерам скидка {promo.get('discount_percent')}% "
                    "по будням 11:00–16:00 при документе."
                )

    parts = []
    for promo in items:
        name = promo.get("name")
        percent = promo.get("discount_percent")
        if name and percent:
            parts.append(f"{name}: {percent}%")
    if parts:
        stacking = promotions.get("stacking")
        stacking_text = f" {stacking}." if stacking else ""
        return "Официальные акции: " + "; ".join(parts) + "." + stacking_text
    return "Скидки действуют только по официальным акциям."


def build_consult_reply(
    message: str,
    *,
    client_slug: str | None = "demo_salon",
    intent_decomp: dict | None = None,
) -> DemoSalonDecision | None:
    normalized = _normalize_text(message)
    if not normalized or _should_skip_consult(normalized, message):
        return None

    consult_intent = False
    consult_topic = None
    consult_question = None
    if isinstance(intent_decomp, dict):
        consult_intent = intent_decomp.get("consult_intent") is True
        consult_topic = _clean_consult_value(intent_decomp.get("consult_topic"), 4)
        consult_question = _clean_consult_value(intent_decomp.get("consult_question"), 12)

    playbooks = _load_consult_playbooks()
    if not playbooks:
        return None

    playbook = _select_consult_playbook(
        message,
        consult_topic if consult_intent else None,
        playbooks,
        allow_fallback=consult_intent,
    )
    if not playbook and not consult_intent:
        playbook = _select_consult_playbook(
            message,
            None,
            playbooks,
            allow_fallback=False,
        )
    if not playbook:
        return None

    action_raw = playbook.get("action")
    action = str(action_raw).strip().lower() if isinstance(action_raw, str) else "reply"
    if action not in {"reply", "escalate"}:
        action = "reply"

    playbook_id = str(playbook.get("id") or playbook.get("topic") or "general").strip()
    consult_question_final = consult_question or _clean_consult_value(message, 12) or ""

    meta: dict[str, Any] = {
        "consult_intent": True,
        "consult_topic": playbook_id or "general",
        "consult_question": consult_question_final,
    }

    if action == "escalate":
        escalation_message = str(playbook.get("escalation_message") or "").strip()
        return DemoSalonDecision(
            action="escalate",
            response=escalation_message,
            intent="consult_escalate",
            meta=meta,
        )

    reply, consult_questions, consult_options = _format_consult_reply(playbook)
    if not reply:
        return None
    meta["consult_questions"] = consult_questions
    meta["consult_options"] = consult_options
    return DemoSalonDecision(
        action="reply",
        response=reply,
        intent="consult_reply",
        meta=meta,
    )


def format_reply_from_truth(intent: str, slots: dict | None = None) -> str | None:
    truth = load_yaml_truth()
    slots = slots or {}

    if intent == "location":
        address = truth.get("salon", {}).get("address", {})
        return (
            f"Адрес: {address.get('full')}. "
            f"{address.get('entrance') or ''}".strip()
        )
    if intent == "location_directions":
        address = truth.get("salon", {}).get("address", {})
        landmarks = address.get("landmarks") or []
        if landmarks:
            return landmarks[0]
        return "Подскажите, откуда вам удобнее добираться?"
    if intent == "location_signage":
        signage = truth.get("salon", {}).get("address", {}).get("signage")
        if signage:
            return f"Да, есть {signage}."
        return "Да, вывеска есть."
    if intent == "parking":
        parking = truth.get("salon", {}).get("parking", {})
        details = parking.get("details") or ""
        return details or "Есть парковка рядом с салоном."
    if intent == "hours":
        hours = truth.get("salon", {}).get("hours", {})
        days = hours.get("days")
        open_time = hours.get("open")
        close_time = hours.get("close")
        return f"Работаем {days}, с {open_time} до {close_time}."
    if intent == "services_overview":
        summary = truth.get("salon", {}).get("services_summary")
        if summary:
            return summary
        categories = [
            str(item.get("category", "")).strip()
            for item in (truth.get("price_list", []) if isinstance(truth, dict) else [])
            if isinstance(item, dict) and item.get("category")
        ]
        categories = [item for item in categories if item]
        if categories:
            return "Мы оказываем услуги: " + ", ".join(categories) + "."
        return "Мы салон красоты. Подскажите, какая услуга интересует?"
    if intent == "aftercare_gel_lac":
        aftercare = truth.get("aftercare", {}).get("gel_lac")
        return aftercare or "Подскажите, пожалуйста, какую услугу нужно подсказать по уходу?"
    if intent == "prep_brows_lashes":
        prep = truth.get("preparation", {}).get("brows_lashes")
        return prep or "Подскажите, пожалуйста, какую именно процедуру планируете?"
    if intent == "procedure_combo":
        combo = truth.get("procedure_compatibility", {}).get("face_cleaning_peel_same_day")
        return combo or "Такое сочетание лучше уточнить у администратора."
    if intent == "style_reference":
        reference = truth.get("style_reference", {}).get("ask_photo")
        return reference or "Пришлите, пожалуйста, фото-пример желаемого результата."
    if intent == "service_clarify":
        clarify = truth.get("service_clarify", {}).get("classic_interest")
        return clarify or "Уточните, пожалуйста, какую именно услугу вы имеете в виду?"
    if intent == "duration_or_price_clarify":
        clarify = truth.get("duration_or_price_clarify")
        if clarify:
            return str(clarify).strip()
        return "Вас интересует цена или длительность? Какая услуга?"
    if intent == "price_manicure":
        quick_price = truth.get("price_quick_answers", {}).get("manicure")
        return quick_price or "Подскажите, какой именно маникюр интересует?"
    if intent == "system_error":
        system_msg = truth.get("system_messages", {}).get("webhook_error")
        return system_msg or "Похоже, была техническая ошибка. Напишите вопрос ещё раз, я на связи."
    if intent == "last_appointment":
        last_time = truth.get("salon", {}).get("hours", {}).get("last_appointment")
        if last_time:
            return f"Последняя запись обычно на {last_time}."
        return "Последняя запись обычно за 30–60 минут до закрытия."
    if intent == "price_query":
        item = slots.get("price_item")
        if item:
            return _format_price_reply(item)
        return "Подскажите, какая услуга интересует? Сориентирую по цене."
    if intent == "why_price_from":
        reason = truth.get("pricing", {}).get("price_from_reason")
        return reason or "Цена «от» зависит от деталей услуги."
    if intent == "promotions_rules":
        stacking = truth.get("promotions", {}).get("stacking")
        return stacking or "Скидки не суммируются."
    if intent == "promotions":
        return _format_promotions(truth, slots.get("promotion_intent"))
    if intent == "objection_price":
        hygiene = truth.get("hygiene", {}).get("instrument_processing")
        if hygiene:
            return (
                "Понимаю вопрос. У нас строгая стерилизация инструментов — это про безопасность, "
                "поэтому цена может быть выше."
            )
        return "Цена зависит от качества и безопасности процедур."
    if intent == "booking_intake":
        return (
            "Могу передать администратору запрос на запись. "
            "Напишите, пожалуйста: услуга, точная дата, точное время, имя, контактный номер."
        )
    if intent == "cancel_policy":
        notice = truth.get("booking", {}).get("cancel_policy", {}).get("notice", {})
        standard = notice.get("standard_services_min_hours")
        long_services = notice.get("long_services_min_hours")
        return (
            f"Для стандартных услуг — минимум за {standard} часа, "
            f"для длительных (3+ часа) — за {long_services} часа."
        )
    if intent == "lateness_ok":
        notes = truth.get("booking", {}).get("lateness_policy", {}).get("notes")
        return notes or "Если опоздание до 10–15 минут — постараемся принять."
    if intent == "guest_child" or intent == "guest_partner":
        guest = truth.get("guest_policy", {}).get("allowed_guests")
        return guest or "Можно, есть зона ожидания."
    if intent == "guest_animals":
        animals = truth.get("guest_policy", {}).get("animals")
        return animals or "С животными нельзя по гигиене."
    if intent == "guest_early":
        early = truth.get("guest_policy", {}).get("early_arrival")
        return early or "Можно прийти на 10–15 минут раньше и подождать."
    if intent == "hygiene":
        hygiene = truth.get("hygiene", {})
        parts = [
            hygiene.get("instrument_processing"),
            hygiene.get("dry_heat"),
            hygiene.get("disposables"),
        ]
        return " ".join([p for p in parts if p])
    if intent == "hygiene_dry_heat":
        return "Да, есть сухожарный шкаф."
    if intent == "hygiene_disposables":
        return "Да, пилки и бафы одноразовые."
    if intent == "brands":
        brands = truth.get("brands", {})
        hair = ", ".join(brands.get("hair", []) if isinstance(brands, dict) else [])
        nails = ", ".join(brands.get("nails", []) if isinstance(brands, dict) else [])
        face = ", ".join(brands.get("face", []) if isinstance(brands, dict) else [])
        return f"Волосы: {hair}. Ногти: {nails}. Лицо: {face}."
    if intent == "amenities_wifi":
        wifi = truth.get("salon", {}).get("amenities", {}).get("wifi")
        return f"{wifi or 'Бесплатный Wi‑Fi'}."
    if intent == "amenities_drinks":
        drinks = truth.get("salon", {}).get("amenities", {}).get("drinks")
        return f"{drinks or 'Чай/кофе бесплатно'}."
    if intent == "amenities_toilet":
        toilet = truth.get("salon", {}).get("amenities", {}).get("toilet")
        return toilet or "Есть туалет для клиентов."
    if intent == "gift_certificate":
        gift = truth.get("salon", {}).get("amenities", {}).get("gift_certificates")
        return gift or "Можно купить сертификат на любую сумму."
    if intent == "off_topic":
        return "Я помогаю только с вопросами о наших услугах салона — цены, запись, адрес."
    return None


def _detect_promotion_intent(normalized: str) -> str | None:
    if any(keyword in normalized for keyword in ["перв", "первое", "первый"]):
        return "promotion_first_visit"
    if "именин" in normalized or "день рождения" in normalized:
        return "promotion_birthday"
    if "студент" in normalized or "пенсион" in normalized:
        return "promotion_student"
    return None


_SELF_RESOLVE_PAYMENT_PATTERNS = (
    re.compile(r"\bпо оплате\b.*\b(уточню|спрошу|узнаю|разберусь|позже)\b"),
    re.compile(r"\b(уточню|спрошу|узнаю|разберусь|позже)\b.*\bпо оплате\b"),
    re.compile(r"\bс оплатой\b.*\b(разберусь|позже)\b"),
    re.compile(r"\b(разберусь|позже)\b.*\bс оплатой\b"),
    re.compile(r"\bоплат\w*\b.*\b(уточню|спрошу|узнаю|разберусь|позже)\b"),
    re.compile(r"\b(уточню|спрошу|узнаю|разберусь|позже)\b.*\bоплат\w*\b"),
)


def _is_self_resolve_payment(normalized: str) -> bool:
    if "оплат" not in normalized:
        return False
    return any(pattern.search(normalized) for pattern in _SELF_RESOLVE_PAYMENT_PATTERNS)


def _detect_policy_intent(normalized: str, phrase_intents: set[str]) -> str | None:
    def _contains_keyword(keyword: str) -> bool:
        if not keyword:
            return False
        if len(keyword) <= 3:
            return re.search(rf"\b{re.escape(keyword)}\b", normalized) is not None
        return keyword in normalized

    skip_payment = _is_self_resolve_payment(normalized)
    payment_keywords = [
        "kaspi",
        "каспи",
        "red",
        "ред",
        "рассроч",
        "долям",
        "pay",
        "оплат",
        "предоплат",
        "перевод",
        "перечис",
        "квитанц",
        "qr",
        "карт",
        "терминал",
        "эквайр",
        "касса",
        "счет",
        "счёт",
        "реквизит",
        "iban",
        "swift",
        "налич",
        "безнал",
        "чек",
    ]
    if not skip_payment and ("payment" in phrase_intents or any(_contains_keyword(keyword) for keyword in payment_keywords)):
        return "policy_payment"

    reschedule_keywords = [
        "перенес",
        "перенести",
        "перенос",
        "переносит",
        "переносить",
        "перезапис",
        "перезапиш",
        "перепис",
        "сдвин",
        "передвин",
        "перемест",
        "изменить запись",
        "поменять время",
        "поменять дату",
        "изменить дату",
        "на другое время",
        "на другой день",
        "на другую дату",
    ]
    if _contains_any(normalized, reschedule_keywords):
        return "policy_reschedule"

    cancel_keywords = ["отмен", "отмена", "откаж", "не приду"]
    if _contains_any(normalized, cancel_keywords):
        return "policy_cancel"

    medical_keywords = [
        "беремен",
        "аллерг",
        "противопоказ",
        "кормл",
        "лактац",
        "ожог",
        "ожг",
        "жжет",
        "жжёт",
        "печет",
        "печёт",
        "болит",
        "больно",
        "кров",
        "воспал",
        "покрасн",
        "сып",
        "реакц",
        "раздраж",
        "анестез",
        "обезбол",
        "кож",
        "дермат",
        "болезн",
        "лиценз",
        "медобраз",
    ]
    if _contains_any(normalized, medical_keywords):
        return "policy_medical"

    legal_keywords = [
        "договор",
        "оферт",
        "юрид",
        "юрист",
        "закон",
        "суд",
        "иск",
        "ответствен",
        "компенсац",
        "штраф",
        "прав потреб",
    ]
    if _contains_any(normalized, legal_keywords):
        return "policy_legal"

    hours_like = _looks_like_hours_question(normalized)
    complaint_keywords = [
        "не понрав",
        "жалоб",
        "претенз",
        "разочар",
        "плохо",
        "недовол",
        "ужас",
        "кошмар",
        "хам",
        "грубо",
        "брак",
        "треснул",
        "отпал",
        "слезл",
        "сломал",
        "испор",
        "задерж",
        "жду уже",
        "не приш",
        "сожг",
        "обожг",
        "порез",
        "кров",
        "не слыш",
        "одно и то же",
        "одно и тоже",
    ]
    if ("complaint" in phrase_intents or _contains_any(normalized, complaint_keywords)) and not hours_like:
        return "policy_complaint"

    discount_keywords = ["скидк", "скидоч", "скидос", "дешевл", "подешевле", "купон", "акци", "промо", "промокод", "торг", "уступ"]
    if _contains_any(normalized, discount_keywords):
        return "policy_discount"

    return None


def get_demo_salon_service_decision(
    message: str,
    client_slug: str | None = "demo_salon",
    intent_decomp: dict | None = None,
) -> DemoSalonDecision | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None
    segments = _split_question_segments(message)
    kinds_seen: set[str] = set()
    for segment in segments:
        question_types = semantic_question_type(
            segment,
            include_kinds={"hours", "pricing", "duration"},
            return_multi=True,
        )
        if isinstance(question_types, list):
            for question in question_types:
                if hasattr(question, "kind") and isinstance(getattr(question, "kind"), str):
                    kinds_seen.add(question.kind)
        elif question_types and hasattr(question_types, "kind"):
            kind = getattr(question_types, "kind")
            if isinstance(kind, str):
                kinds_seen.add(kind)
    if "hours" in kinds_seen and {"pricing", "duration"} & kinds_seen:
        return None
    if not _looks_like_service_question(normalized, message):
        return None

    service_query_meta = _resolve_service_query_meta(
        message,
        client_slug,
        intent_decomp,
        require_query=True,
    )
    service = _match_service(normalized)
    truth = load_yaml_truth()
    if service:
        reply = _format_service_reply(service, truth)
        if reply:
            return DemoSalonDecision(
                action="reply",
                response=reply,
                intent="service_match",
                meta=service_query_meta,
            )

    reply = _format_service_not_found_reply()
    if reply:
        return DemoSalonDecision(
            action="reply",
            response=reply,
            intent="service_not_found",
            meta=service_query_meta,
        )
    return None


def get_demo_salon_decision(
    message: str,
    client_slug: str | None = "demo_salon",
    intent_decomp: dict | None = None,
) -> DemoSalonDecision | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None

    phrase_intents = phrase_match_intent(message)
    if "отмен" in normalized and "за сколько" in normalized:
        reply = format_reply_from_truth("cancel_policy")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="cancel_policy")

    policy_intent = _detect_policy_intent(normalized, phrase_intents)

    if policy_intent == "policy_payment":
        return DemoSalonDecision(
            action="escalate",
            response="По оплате уточню у администратора — передам администратору ваш вопрос.",
            intent="payment",
        )
    if policy_intent == "policy_reschedule":
        return DemoSalonDecision(
            action="escalate",
            response="Перенос записи подтверждает администратор. Передам ваш запрос.",
            intent="reschedule",
        )
    if policy_intent == "policy_cancel":
        return DemoSalonDecision(
            action="escalate",
            response=(
                "Администратор подтвердит отмену. "
                "Напишите, пожалуйста: имя, услуга, контактный номер."
            ),
            intent="cancel_request",
            collect=["имя", "услуга", "контактный номер"],
        )
    if policy_intent == "policy_medical":
        return DemoSalonDecision(
            action="escalate",
            response=(
                "По таким вопросам нужна консультация мастера или администратора — "
                "передам ваш вопрос."
            ),
            intent="medical",
        )
    if policy_intent == "policy_legal":
        return DemoSalonDecision(
            action="escalate",
            response="По юридическим вопросам подключу администратора — передам ваш запрос.",
            intent="legal",
        )
    if policy_intent == "policy_complaint":
        return DemoSalonDecision(
            action="escalate",
            response="Жаль, что так вышло. Передам администратору, чтобы разобрались.",
            intent="complaint",
        )

    if "сегодня" in normalized or "прямо сейчас" in normalized:
        if _contains_any(normalized, ["запис", "окошк", "свободн"]):
            return DemoSalonDecision(
                action="escalate",
                response=(
                    "На сегодня уточню у администратора. Подскажите, пожалуйста: услуга и удобное время — передам."
                ),
                intent="same_day_booking",
                collect=["услуга", "время"],
            )

    consult_decision = build_consult_reply(
        message,
        client_slug=client_slug,
        intent_decomp=intent_decomp,
    )
    if consult_decision:
        return consult_decision

    if "скидки сумм" in normalized or "скидк" in normalized and "сумм" in normalized:
        reply = format_reply_from_truth("promotions_rules")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="promotions_rules")

    promotion_intent = _detect_promotion_intent(normalized)
    if promotion_intent:
        reply = format_reply_from_truth("promotions", {"promotion_intent": promotion_intent})
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="promotions")

    if policy_intent == "policy_discount":
        reply = _format_promotions(load_yaml_truth())
        return DemoSalonDecision(action="reply", response=reply, intent="discount_haggle")

    if "почему" in normalized and "от" in normalized and ("цена" in normalized or "стоим" in normalized):
        reply = format_reply_from_truth("why_price_from")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="why_price_from")

    if "дороже" in normalized or ("дорог" in normalized and "скид" not in normalized):
        reply = format_reply_from_truth("objection_price")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="objection_price")

    if "адрес" in normalized or "где вы" in normalized or "где наход" in normalized:
        reply = format_reply_from_truth("location")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="location")

    if "остановк" in normalized or "как пройти" in normalized or "как добрат" in normalized or "как доехать" in normalized:
        reply = format_reply_from_truth("location_directions")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="location_directions")

    if "вывеск" in normalized:
        reply = format_reply_from_truth("location_signage")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="location_signage")

    if "парков" in normalized:
        reply = format_reply_from_truth("parking")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="parking")

    if "последняя запись" in normalized or "до какого времени можно запис" in normalized:
        reply = format_reply_from_truth("last_appointment")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="last_appointment")

    multi_result = compose_multi_truth_reply(
        message,
        client_slug or "demo_salon",
        intent_decomp=intent_decomp,
        return_meta=True,
    )
    if multi_result:
        multi_reply, multi_meta = multi_result
        return DemoSalonDecision(
            action="reply",
            response=multi_reply,
            intent="multi_truth",
            meta=multi_meta if isinstance(multi_meta, dict) else None,
        )

    if "опозда" in normalized:
        minutes = _extract_minutes(message)
        tolerated = load_yaml_truth().get("booking", {}).get("lateness_policy", {}).get("tolerated_minutes", 15)
        try:
            tolerated = int(tolerated)
        except (TypeError, ValueError):
            tolerated = 15
        if minutes is not None and minutes > tolerated:
            return DemoSalonDecision(
                action="escalate",
                response="Если опоздание больше 15 минут — передам администратору, чтобы уточнить.",
                intent="lateness_over",
            )
        reply = format_reply_from_truth("lateness_ok")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="lateness_ok")

    hours_like = _looks_like_hours_question(normalized) or _contains_any(
        normalized,
        ["ашык", "ашық", "бугин", "бүгін"],
    )
    if hours_like and not _contains_any(normalized, ["косметик", "материал", "бренд", "марки"]):
        reply = format_reply_from_truth("hours")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="hours")

    if "services_overview" in phrase_intents or _contains_any(
        normalized,
        [
            "чем занимает",
            "какие услуги",
            "что вы делаете",
            "что у вас есть",
            "какой спектр услуг",
            "какие процедуры",
            "что можно сделать",
        ],
    ):
        reply = format_reply_from_truth("services_overview")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="services_overview")

    if "aftercare_gel_lac" in phrase_intents or (
        "гель лак" in normalized
        and _contains_any(normalized, ["ухаж", "продл", "держ", "нос", "срок"])
    ):
        reply = format_reply_from_truth("aftercare_gel_lac")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="aftercare_gel_lac")

    if "prep_brows_lashes" in phrase_intents or (
        "подготов" in normalized and _contains_any(normalized, ["бров", "ресниц"])
    ):
        reply = format_reply_from_truth("prep_brows_lashes")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="prep_brows_lashes")

    if "procedure_combo" in phrase_intents or (
        _contains_any(normalized, ["совмещ", "в один день"]) and _contains_any(normalized, ["чистк", "пилинг"])
    ):
        reply = format_reply_from_truth("procedure_combo")
        if reply:
            return DemoSalonDecision(action="escalate", response=reply, intent="procedure_combo")

    if "style_reference" in phrase_intents:
        reply = format_reply_from_truth("style_reference")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="style_reference")

    if "system_error" in phrase_intents or "ошибка вызова вебхука" in normalized:
        reply = format_reply_from_truth("system_error")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="system_error")

    if "service_clarify" in phrase_intents or ("классическ" in normalized and "интерес" in normalized):
        reply = format_reply_from_truth("service_clarify")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="service_clarify")

    if _contains_any(normalized, ["ребен", "ребён"]) or _contains_any_words(
        normalized, ["муж", "мужем", "мужу", "мужа"]
    ):
        reply = format_reply_from_truth("guest_child")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="guest_policy")

    if _contains_any(normalized, ["собак", "животн"]):
        reply = format_reply_from_truth("guest_animals")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="guest_policy")

    if _contains_any(normalized, ["пораньше", "раньше", "подождать"]):
        reply = format_reply_from_truth("guest_early")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="guest_policy")

    question_type = semantic_question_type(message)
    question_meta: dict[str, Any] | None = None
    if question_type:
        question_meta = {
            "question_type": question_type.kind,
            "question_type_score": question_type.score,
        }
        if question_type.kind == "duration":
            service_query_meta = _resolve_service_query_meta(
                message,
                client_slug,
                intent_decomp,
                require_query=True,
            )
            service = _resolve_service_from_query(service_query_meta.get("service_query"))
            reply = _format_service_duration_reply(service)
            return DemoSalonDecision(
                action="reply",
                response=reply,
                intent="service_duration",
                meta={**question_meta, **service_query_meta} if question_meta else service_query_meta,
            )
    elif _has_duration_signal(normalized, message):
        service_query_meta = _resolve_service_query_meta(
            message,
            client_slug,
            intent_decomp,
            require_query=True,
        )
        service = _resolve_service_from_query(service_query_meta.get("service_query"))
        reply = _format_service_duration_reply(service)
        return DemoSalonDecision(
            action="reply",
            response=reply,
            intent="service_duration",
            meta={"question_type": "duration", **service_query_meta},
        )

    price_signal = _has_price_signal(normalized, message)
    price_item = _find_best_price_item(message)
    if not price_item and isinstance(intent_decomp, dict):
        price_service_meta = _resolve_service_query_meta(
            message,
            client_slug,
            intent_decomp,
            require_query=False,
        )
        service_query = price_service_meta.get("service_query") if isinstance(price_service_meta, dict) else None
        if isinstance(service_query, str) and service_query.strip():
            price_item = _find_best_price_item(service_query)
    if question_type is None and (price_item or price_signal):
        if _is_offtopic_message(normalized):
            reply = format_reply_from_truth("off_topic")
            if reply:
                return DemoSalonDecision(action="reply", response=reply, intent="off_topic")
        reply = format_reply_from_truth("duration_or_price_clarify")
        if reply:
            return DemoSalonDecision(
                action="reply",
                response=reply,
                intent="duration_or_price_clarify",
            )

    question_meta_for_price = question_meta if question_type and question_type.kind == "pricing" else None
    if "price_manicure" in phrase_intents or (
        _contains_any(normalized, ["маникюр", "маник"]) and price_signal and not price_item
    ):
        service_query_meta = _resolve_service_query_meta(
            message,
            client_slug,
            intent_decomp,
            require_query=True,
        )
        if service_query_meta.get("service_query"):
            reply = format_reply_from_truth("price_manicure")
            if reply:
                meta = {**question_meta_for_price, **service_query_meta} if question_meta_for_price else service_query_meta
                return DemoSalonDecision(
                    action="reply",
                    response=reply,
                    intent="price_manicure",
                    meta=meta,
                )

    if _contains_any(normalized, ["стерилиз", "инструмент", "обрабатываете", "дез", "сухожар"]):
        reply = format_reply_from_truth("hygiene")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="hygiene")

    if _contains_any(normalized, ["сухожар"]):
        reply = format_reply_from_truth("hygiene_dry_heat")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="hygiene")

    if _contains_any(normalized, ["пилк", "однораз"]):
        reply = format_reply_from_truth("hygiene_disposables")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="hygiene")

    if _contains_any(normalized, ["какой космет", "материал", "бренд", "марки"]):
        reply = format_reply_from_truth("brands")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="brands")

    if _contains_any(normalized, ["wifi", "вайфай", "вай фай", "wi fi"]):
        reply = format_reply_from_truth("amenities_wifi")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="amenities")

    if _contains_any(normalized, ["кофе", "чай"]):
        reply = format_reply_from_truth("amenities_drinks")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="amenities")

    if _contains_any(normalized, ["туалет", "санузел"]):
        reply = format_reply_from_truth("amenities_toilet")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="amenities")

    if "сертификат" in normalized:
        reply = format_reply_from_truth("gift_certificate")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="gift_certificate")

    if (
        "order_booking" in phrase_intents
        or _contains_any(normalized, ["запис", "запиш", "окошк", "свободн"])
    ):
        reply = format_reply_from_truth("booking_intake")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="booking_intake")

    service_decision = get_demo_salon_service_decision(
        message,
        client_slug=client_slug or "demo_salon",
        intent_decomp=intent_decomp,
    )
    if service_decision:
        return service_decision

    if _is_offtopic_message(normalized):
        reply = format_reply_from_truth("off_topic")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="off_topic")

    if price_item or price_signal:
        service_query_meta = _resolve_service_query_meta(
            message,
            client_slug,
            intent_decomp,
            require_query=True,
        )
        if not service_query_meta.get("service_query"):
            reply = format_reply_from_truth("service_clarify")
            if reply:
                return DemoSalonDecision(
                    action="reply",
                    response=reply,
                    intent="service_clarify",
                    meta=service_query_meta,
                )
        reply = format_reply_from_truth("price_query", {"price_item": price_item["item"]} if price_item else {})
        if reply:
            meta = {**question_meta_for_price, **service_query_meta} if question_meta_for_price else service_query_meta
            return DemoSalonDecision(
                action="reply",
                response=reply,
                intent="price_query",
                meta=meta,
            )

    return None


def get_demo_salon_price_reply(message: str, client_slug: str | None = "demo_salon") -> str | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None
    service_query_meta = _resolve_service_query_meta(
        message,
        client_slug,
        intent_decomp=None,
        require_query=True,
    )
    if not service_query_meta.get("service_query"):
        return None
    price_item = _find_best_price_item(message)
    if not price_item:
        return None
    return format_reply_from_truth("price_query", {"price_item": price_item["item"]})


def get_demo_salon_price_item(message: str) -> str | None:
    price_item = _find_best_price_item(message)
    if not price_item:
        return None
    item = price_item.get("item")
    if not item:
        return None
    return str(item).strip() or None


def get_truth_reply(message: str) -> str | None:
    decision = get_demo_salon_decision(message)
    if decision and decision.action == "reply":
        return decision.response
    return None
